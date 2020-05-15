package main

import (
        "fmt"

        "database/sql"
        "io/ioutil"
        "strconv"
        "strings"
        "time"

        "github.com/ghodss/yaml"
        _ "github.com/go-sql-driver/mysql"

        "log"

        "github.com/fsnotify/fsnotify"
        "regexp"
		"os/exec"
)

const (
	filePath = "/root/k8s/yaml/"
)

var deploymentID string
var dpTpID string
var appID string

func main() {
        //创建一个监控对象
        watch, err := fsnotify.NewWatcher()
        checkErr(err)
        defer watch.Close()
        //添加要监控的对象，文件或文件夹
        err = watch.Add(filePath)
        checkErr(err)
        //我们另启一个goroutine来处理监控对象的事件
        go func() {
                for {
                        select {
                        case ev := <-watch.Events:
                                {
                                        //判断事件发生的类型，如下5种
                                        // Create 创建
                                        if ev.Op&fsnotify.Create == fsnotify.Create {
                                                //query all files
                                                files, err := ioutil.ReadDir(filePath)
                                                checkErr(err)
                                                for _, f := range files {
                                                        match, _ := regexp.MatchString(`\.yml$`, f.Name())
                                                        if match == true {
                                                                log.Println(f.Name())
                                                                fileName := f.Name()
                                                                fileName = strings.Split(fileName, ".")[0]
                                                                dataArray := strings.Split(fileName, "_")
								if len(dataArray[0]) > 100 {
									log.Println(len(dataArray[0]))
									log.Println("The name of service is too long!")
								} else {
                                                                	if dataArray[1] == "deployment" {
										args := []string{"switchYaml.py", dataArray[0], f.Name()}
										cmd := exec.Command("python", args...)
										if _, err := cmd.Output(); err != nil {
        										fmt.Println(err)
    										}
                                                                        	apID := insertApp(dataArray[0])
                                                                        	dpID := insertDeployment(dataArray[0]+"-deployment", apID)
                                                                        	fmt.Println("apID: " + apID)
                                                                        	fmt.Println("dpID: " + dpID)
                                                                        	insertDeploymentTemplate(dataArray[0]+"-deployment", dataArray[2], f.Name(), dpID)
                                                                	}
								}
                                                        }
                                                }
                                                log.Println("创建文件 : ", ev.Name)
                                        }
                                }
                        case err := <-watch.Errors:
                                {
                                        log.Println("error : ", err)
                                        return
                                }
                        }
                }
        }()

        //循环
        select {}
}

func checkErr(errMasg error) {
        if errMasg != nil {
                panic(errMasg)
        }
}

func queryData(query *sql.Rows) map[int]map[string]string {
        column, _ := query.Columns()              //读出查询出的列字段名
        values := make([][]byte, len(column))     //values是每个列的值，这里获取到byte里
        scans := make([]interface{}, len(column)) //因为每次查询出来的列是不定长的，用len(column)定住当次查询的长度
        for i := range values {                   //让每一行数据都填充到[][]byte里面
                scans[i] = &values[i]
        }
        results := make(map[int]map[string]string) //最后得到的map
        i := 0
        for query.Next() { //循环，让游标往下移动
                if err := query.Scan(scans...); err != nil { //query.Scan查询出来的不定长值放到scans[i] = &values[i],也就是每行都放在values里
                        fmt.Println(err)
                        //return
                }
                row := make(map[string]string) //每行数据
                for k, v := range values {     //每行数据是放在values里面，现在把它挪到row里
                        key := column[k]
                        row[key] = string(v)
                }
                results[i] = row //装入结果集中
                i++
        }
        return results
}

func insertDeploymentTemplate(dpName string, dpTag string, dpFile string, dpID string) {
        file, _ := ioutil.ReadFile(filePath + dpFile)
        jsonData, err := yaml.YAMLToJSON(file)
        checkErr(err)

        db, err := sql.Open("mysql", "wayne:V2F5bmVfeW91eGluMTIz@tcp(10.56.196.13:3306)/?charset=utf8") //第一个参数为驱动名
        checkErr(err)
	defer db.Close()

        //query deployment exist or not, if not create
        var dpTpFlag = false
        qyDpTp := "select id, description, name from wayne.deployment_template;"
        qyDpRes, err := db.Query(qyDpTp)
        checkErr(err)
	defer qyDpRes.Close()
        resData := queryData(qyDpRes)
        for _, v := range resData {
                dpTpUnTag := dpName + dpTag
                vTag := v["name"] + v["description"]
                //fmt.Println("dpTpUnTag:" + dpTpUnTag)
                //fmt.Println("vTag: "+vTag)
                if vTag == dpTpUnTag {
                        dpTpFlag = true
                        break
                }
        }
        if dpTpFlag == false {
                //query max deployment template id
                queryMaxTpID := "select id from  wayne.deployment_template order by id desc limit 1;"
                queryMaxTpIDRes, err := db.Query(queryMaxTpID)
                checkErr(err)
		defer queryMaxTpIDRes.Close()
                resTpID := queryData(queryMaxTpIDRes)
                for _, v := range resTpID {
                        dpTpID = v["id"]
                }

                dpTpIDInt, err := strconv.Atoi(dpTpID)
                checkErr(err)
                dpTpID = strconv.Itoa(dpTpIDInt + 1)
                fmt.Println("dpTpID: " + dpTpID)

                str := strconv.Quote(string(jsonData))
                str = strings.Replace(str, `"{\"`, `{\"`, 1)
                str = strings.Replace(str, `}}}"`, `}}}`, 1)
                currentTime := time.Now().Format("2006-01-02 15:04:05")
                insertDpTp := `insert into wayne.deployment_template  values (` + dpTpID + `, '` + dpName + `', '` + str + `', ` + dpID + `, '` + dpTag + `', '` + currentTime + `', '` + currentTime + `', 'admin', 0);`
                db.Exec(insertDpTp)
                //fmt.Println(insertDpTp)

                log.Println("Insert success!")
        } else {
                log.Println("Insert none!")
        }
}

func insertDeployment(name string, apID string) string {
        db, err := sql.Open("mysql", "wayne:V2F5bmVfeW91eGluMTIz@tcp(10.56.196.13:3306)/?charset=utf8") //第一个参数为驱动名
        checkErr(err)
	defer db.Close()

        //query deployment exist or not, if not create
        deploymentFlag := false
        deploymentName := name
        queryDeployment := "select id, name from wayne.deployment;"
        queryDeploymentRes, err := db.Query(queryDeployment)
        checkErr(err)
	defer queryDeploymentRes.Close()
        resData := queryData(queryDeploymentRes)
        for _, v := range resData {
                if v["name"] == deploymentName {
                        deploymentFlag = true
                        deploymentID = v["id"]
                        break
                }
        }

        if deploymentFlag == false {
                //query max deployment id
                queryMaxID := "select id from  wayne.deployment order by id desc limit 1;"
                queryMaxIDRes, err := db.Query(queryMaxID)
                checkErr(err)
		defer queryMaxIDRes.Close()
                resID := queryData(queryMaxIDRes)
                for _, vid := range resID {
                        deploymentID = vid["id"]
                }
                deploymentIDInt, err := strconv.Atoi(deploymentID)
                checkErr(err)
                deploymentID = strconv.Itoa(deploymentIDInt + 1)

                currentTime := time.Now().Format("2006-01-02 15:04:05")
                deploymentMetaData := `{"replicas":{"yx-k8s":1},"resources":{"cpuLimit":"12","cpuRequestLimitPercent":"50%","memoryLimit":"64","memoryRequestLimitPercent":"100%","replicaLimit":"32"},"privileged":null}`
                insertDeploymentName := "insert into wayne.deployment  values (" + deploymentID + ", '" + deploymentName + "', '" + string(deploymentMetaData) + "', "+ apID +", '', 0, '" + currentTime + "', '" + currentTime + "', 'admin', 0);"
                db.Exec(insertDeploymentName)
        }
        return deploymentID
}

func insertApp(name string) string {
        db, err := sql.Open("mysql", "wayne:V2F5bmVfeW91eGluMTIz@tcp(10.56.196.13:3306)/?charset=utf8") //第一个参数为驱动名
        checkErr(err)
	defer db.Close()

        //query app exist or not, if not create
        appFlag := false
        appName := name
        queryApp := "select id, name from wayne.app;"
        queryAppRes, err := db.Query(queryApp)
        checkErr(err)
	defer queryAppRes.Close()
        resData := queryData(queryAppRes)
        for _, v := range resData {
                if v["name"] == appName {
                        appFlag = true
                        appID = v["id"]
                        break
                }
        }

        if appFlag == false {
                //query max app id
                queryMaxID := "select id from  wayne.app order by id desc limit 1;"
                queryMaxIDRes, err := db.Query(queryMaxID)
                checkErr(err)
		defer queryMaxIDRes.Close()
                resID := queryData(queryMaxIDRes)
                for _, vid := range resID {
                        appID = vid["id"]
                }
                appIDInt, err := strconv.Atoi(appID)
                checkErr(err)
                appID = strconv.Itoa(appIDInt + 1)

                currentTime := time.Now().Format("2006-01-02 15:04:05")
                insertAppName := "insert into wayne.app values (" + appID + ", '" + appName + "', 4, '','"+ appName +"', '" + currentTime + "', '" + currentTime + "', 'fengxiaodong01', 0, 0);"
                db.Exec(insertAppName)
        }
        return appID
}
