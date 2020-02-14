package main

import (
        "fmt"

        "database/sql"

        _ "github.com/go-sql-driver/mysql"

        "log"
	"strconv"
	"time"
	"os"
)

var userID string
var maxAppUserID string
var appID string

func main() {
	if len(os.Args) != 2 {
		fmt.Println("参数数量错误.........")
		help()
	} else {
		insertAppUser(os.Args[1])
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

func insertAppUser(name string) {
        db, err := sql.Open("mysql", "wayne:V2F5bmVfeW91eGluMTIz@tcp(10.56.196.13:3306)/?charset=utf8") //第一个参数为驱动名
        checkErr(err)

        //query user exist or not
        userFlag := false
        userName := name
        queryUser := "select id, name from wayne.user;"
        queryUserRes, err := db.Query(queryUser)
        checkErr(err)
        resData := queryData(queryUserRes)
        for _, v := range resData {
                if v["name"] == userName {
                        userFlag = true
                        userID = v["id"]
			fmt.Println("userid: " + userID)
                        break
                }
        }

        if userFlag == false {
		log.Println(userName+" is none!")
        } else {
		//query app id
		queryApp := "select id from wayne.app where namespace_id=4 order by id desc;"
		queryAppRes, err := db.Query(queryApp)
		checkErr(err)
		resApp := queryData(queryAppRes)		
		for _, u := range resApp {
			//fmt.Println("appid: " + u["id"])
			appID = u["id"]
			
			//query repeat data
			reFlag := false
			queryReData := "select app_id, user_id from wayne.app_user where group_id=23 and user_id="+userID+";"
			queryReDataRes, err := db.Query(queryReData)
			checkErr(err)
			reRes := queryData(queryReDataRes)
			for _, re := range reRes {
				if re["app_id"]==appID {
					reFlag = true
					break
				}
			}
			
			if reFlag == false {
				//query max app_user id
				queryMaxAppUserID := "select id from wayne.app_user order by id desc limit 1;"
				queryMaxAppUserIDRes, err := db.Query(queryMaxAppUserID)
				checkErr(err)
				resID := queryData(queryMaxAppUserIDRes)
				for _, vid := range resID {
					maxAppUserID = vid["id"]
				}
				maxAppUserIDInt, err := strconv.Atoi(maxAppUserID)
				checkErr(err)
				maxAppUserID = strconv.Itoa(maxAppUserIDInt+1)

				currentTime := time.Now().Format("2006-01-02 15:04:05")
				appUser := "insert into wayne.app_user values (" + maxAppUserID + ", " + appID + ", " + userID + ", 23, '" + currentTime + "', '" + currentTime + "');" 
				//fmt.Println("appUser: " + appUser)
				db.Query(appUser)
			} else {
				log.Println("appID: "+appID+",userID: "+userID+" is repeat!")
			}
		}
	}
}

// display help information
func help() {
	fmt.Println("参数：")
	fmt.Println("user: 指定用户名")
	fmt.Println("----------------")
	fmt.Println("eg: addAppUser fengxiaodong01")
}
