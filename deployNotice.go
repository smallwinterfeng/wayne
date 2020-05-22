package main

import (
	"fmt"
	"log"
	"net/http"
	"io/ioutil"
	"encoding/json"
	"bytes"
	"time"
	"strings"
	"database/sql"
	_ "github.com/go-sql-driver/mysql"
)

const (
	optoolsToken = "b3B0b29scw=="
)

type Containers struct {
	Image string `json:"image"`
}

type Spec1 struct {
	Containers []Containers `json:"containers"`
}

type Template struct {
	Spec1 Spec1 `json:"spec"`
}

type Spec2 struct {
	Replicas int64 `json:"replicas"`
	Template Template `json:"template"`
}

type Object struct {
	Spec2 Spec2 `json:"spec"`
}

type Deployment struct {
	Cluster string `json:"cluster"`
	Object Object
	ResourceId int64 `json:"resourceId"`
        ResourceName string `json:"resourceName"`
        Status int64 `json:"status"`
        TemplateId int64 `json:"templateId"`
        Type int64 `json:"type"`
}

type NameSpace struct {
	Id string `json:"id"`
	Name string `json:"name"`
	User string `json:"user"`
}

type Payload struct {
	Action string `json:"action"`
	Deployment Deployment
}

type Webhook struct {
	Event string `json:"event"`
	NameSpace NameSpace
	User string `json:"user"`
	Payload Payload
}

func wechatNotification(alarmContent string) {
    //product group
    wechatURL := "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=49c2e884-897e-479c-ae11-bbb4aa80f436"
    //Test group owner
    //wechatURL := "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=698eb818-8a1d-4e40-87b1-69e918093761"
    content, data := make(map[string]string), make(map[string]interface{})    
    content["content"] = alarmContent      
    data["msgtype"] = "markdown"     
    data["markdown"] = content        
    jsonValue, _ := json.Marshal(data)    
    fmt.Println(jsonValue)
    
    resp, _ := http.Post(wechatURL, "application/json", bytes.NewBuffer(jsonValue))
    fmt.Println("resp")
    fmt.Println(resp) 
}

func handleWebhook(w http.ResponseWriter, r *http.Request) {
	var webhook Webhook
	var status string
	body, _ := ioutil.ReadAll(r.Body)
        json.Unmarshal(body, &webhook)
	//fmt.Println(string(body))
	action := webhook.Payload.Action
	if action == "UpgradeDeployment" {
		imageArray := strings.Split(webhook.Payload.Deployment.Object.Spec2.Template.Spec1.Containers[0].Image, ":")
		imageTag := imageArray[len(imageArray) - 1]
		nameSpace := webhook.NameSpace.Name
		resourceName := webhook.Payload.Deployment.ResourceName
		user := webhook.User
		if webhook.Payload.Deployment.Status == int64(1) {
			status = "success"
		} else {
			status = "failed"
		}
		createTime := time.Now().Format("2006-01-02 15:04:05")
		action = "UpgradeDeployment"
	
		var title string
                switch nameSpace {
			case "ops-system":
				title = "运维"
			case "hq-system":
				title = "行情"
			case "zx-system":
				title = "资讯"
			case "jy-system":
				title = "交易"
		}
		content := title+"项目：" + resourceName + "\n >操作人：" + user + "\n >动作：" + action + "\n >空间：" + nameSpace + "\n >镜像版本：" + imageTag + "\n >状态：" + status + "\n >时间：" + createTime
		wechatNotification(content)
		//log.Println(content)

		//update wayne description and delete invalid deployment_template
		if nameSpace == "hq-system" {
			go updateDescription()
			go deleteDeploymentTemplate()
		}
	} else if action == "OfflineDeployment" {
		resourceName := webhook.Payload.Deployment.ResourceName
		nameSpace := webhook.NameSpace.Name

                var title string
                switch nameSpace {
                        case "ops-system":
                                title = "运维"
                        case "hq-system":
                                title = "行情"
                        case "zx-system":
                                title = "资讯"
                        case "jy-system":
                                title = "交易"
                }
		user := webhook.User
		action = "OfflineDeployment"
		createTime := time.Now().Format("2006-01-02 15:04:05")
		content := title+"项目：" + resourceName + "\n >操作人：" + user + "\n >动作：" + action + "\n >空间：" + nameSpace + "\n >时间：" + createTime
		wechatNotification(content)
		//log.Println(content)
	} 
}

func handleWebhookOptools(w http.ResponseWriter, r *http.Request) {
	token := r.FormValue("token")
	//fmt.Println(token)
	if token == optoolsToken {
		//update wayne description and delete invalid deployment_template
		go updateDescription()
		go deleteDeploymentTemplate()
	} else {
		log.Println("The token is error! Please check")	
	}
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
	defer queryPublishRes.Close()

        resData := queryData(queryPublishRes)
        for _, v := range resData {
		resourceID := v["resource_id"]
		templateID := v["template_id"]
		
		//query template description
		var templateDescription string
		queryTemplate := "select description from wayne.deployment_template where id=" + templateID + ";"
		queryTemplateRes, err := db.Query(queryTemplate)
		checkErr(err)
		defer queryTemplateRes.Close()

		resTemplateData := queryData(queryTemplateRes)
		for _, vT := range resTemplateData {
			templateDescription = vT["description"]
		}

		//query app id from deployment
		var appID string
		queryDeployment := "select app_id from wayne.deployment where id=" + resourceID + ";"
		queryDeploymentRes, err := db.Query(queryDeployment)
		checkErr(err)
		defer queryDeploymentRes.Close()

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
			defer queryAppRes.Close()

			resAppData := queryData(queryAppRes)
			for _, vA := range resAppData {
				namespaceID = vA["namespace_id"]
			}
			if namespaceID == "4" {
				//update the description of app from publish_status
				updateSql := "update wayne.app set description='" + templateDescription + "' where id=" + appID + ";"
				row , err := db.Query(updateSql)
				checkErr(err)
				defer row.Close()
			}
		}
        }
}

func deleteDeploymentTemplate() {
        db, err := sql.Open("mysql", "wayne:V2F5bmVfeW91eGluMTIz@tcp(10.56.196.13:3306)/?charset=utf8") //第一个参数为驱动名
        checkErr(err)
        defer db.Close()

	//delete the template of deployment
	deleteSql := "delete from wayne.deployment_template where deleted=1;"
	row, err := db.Query(deleteSql)
	checkErr(err)
	defer row.Close()
}


func main() {
	log.Println("server started")
	http.HandleFunc("/webhook", handleWebhook)
	http.HandleFunc("/webhookOptools", handleWebhookOptools)
	log.Fatal(http.ListenAndServe(":8089", nil))
}
