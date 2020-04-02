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
    //Test group
    wechatURL := "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=fbef7c8b-c0bd-49d0-8b24-0a9c261ebcc5"
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
	} 
}

func main() {
    log.Println("server started")
	http.HandleFunc("/webhook", handleWebhook)
	log.Fatal(http.ListenAndServe(":8089", nil))
}
