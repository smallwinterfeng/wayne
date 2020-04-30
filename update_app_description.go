package main

import (
	"fmt"
	"database/sql"
	 _ "github.com/go-sql-driver/mysql"
	"github.com/fsnotify/fsnotify"
	"log"
)

func main() {
        //创建一个监控对象
        watch, err := fsnotify.NewWatcher()
        checkErr(err)
        defer watch.Close()
        //添加要监控的对象，文件或文件夹
        err = watch.Add("/root/k8s/yaml/")
        checkErr(err)
        //我们另启一个goroutine来处理监控对象的事件
		go func() {
			for {
				select {
				case ev := <-watch.Events:
					{
						//判断事件发生的类型
						//Create 创建
						if ev.Op&fsnotify.Create == fsnotify.Create {
							updateDescription()	
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

func updateDescription() {
        db, err := sql.Open("mysql", "wayne:V2F5bmVfeW91eGluMTIz@tcp(10.56.196.13:3306)/?charset=utf8") //第一个参数为驱动名
        checkErr(err)
		defer db.Close()

        //query publish status
        queryPublish := "select resource_id, template_id from wayne.publish_status where type=0;"
        queryPublishRes, err := db.Query(queryPublish)
        checkErr(err)
        resData := queryData(queryPublishRes)
        for _, v := range resData {
				resourceID := v["resource_id"]
				templateID := v["template_id"]
				
				//query template description
				var templateDescription string
				queryTemplate := "select description from wayne.deployment_template where id=" + templateID + ";"
				queryTemplateRes, err := db.Query(queryTemplate)
				checkErr(err)
				resTemplateData := queryData(queryTemplateRes)
				for _, vT := range resTemplateData {
					templateDescription = vT["description"]
				}

				//query app id from deployment
				var appID string
				queryDeployment := "select app_id from wayne.deployment where id=" + resourceID + ";"
				queryDeploymentRes, err := db.Query(queryDeployment)
				checkErr(err)
				resDeploymentData := queryData(queryDeploymentRes)
				for _, vD := range resDeploymentData {
					appID = vD["app_id"]
				}
				
				//judge app is hq or not
				if len(appID) >= 1 {
					var namespaceID string
					queryApp := "select namespace_id from wayne.app where id=" + appID + ";"
					queryAppRes, err := db.Query(queryApp)
					checkErr(err)
					resAppData := queryData(queryAppRes)
					for _, vA := range resAppData {
						namespaceID = vA["namespace_id"]
					}
					if namespaceID == "4" {
						//update the description of app from publish_status
						updateSql := "update wayne.app set description='" + templateDescription + "' where id=" + appID + ";"
						db.Query(updateSql)
					}
				}
        }
}
