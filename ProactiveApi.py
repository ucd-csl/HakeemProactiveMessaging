import random
import requests
import pymongo as pm
import datetime
from dateutil.parser import parse
import time
import json


class ProactiveApi:
    uri = "" #Insert Mongo/CosmosDB pathway here

    def __init__(self):
        self.client = pm.MongoClient(self.uri)
        self.db = self.client.hakeemdb
        self.user_col = self.db.users
        self.course_col = self.db.hakeem_course_list
        self.host = "" #Insert API URL here
        #self.host = "http://localhost:3979/api/ProactiveApi"

    def checkUserActivity(self):
        for user in self.user_col.find({"conversationReference.ChannelId": "skype"}):
            interest = user["interests"]
            if "Computers" in interest or "Video Games" in interest:
                interest.append("Technology")
            elif "Sports" in interest:
                interest.append("Fitness")
            elif "Reading" in interest or "Writing" in interest:
                interest.append("Creative Writing")
            elif "Economics" in interest or "Finance" in interest:
                interest.append("Economics and Finance")
            elif "Nature" in interest:
                interest.append("Biology")
            print("user", user["Name"])
            # last = datetime.datetime.fromtimestamp(user["lastActive"])
            last = user["lastActive"]
            print(user["lastNotified"])
            time_since = datetime.datetime.utcnow() - last
            # if user hasn't been active in a year, delete their user profile
            if time_since.days >= 365:
                self.user_col.delete_one({"_id": user["_id"]})
            elif user["Notification"] == 0:
                print("Notifications off")
            # if user has been notified in a while and hasn't been talking to the bot in the past 10 minutes
            elif user["lastNotified"] >= user["Notification"] and time_since.total_seconds() >= 600:
                self.user_col.find_one_and_update({"_id": user["_id"]}, {"$set": {"lastNotified": 1}})
                courses = list(self.getnewCourses())
                if len(courses) == 0:
                    # if no new courses could be found than send fail message to bot and exit
                    payload = {
                        "Text": "fail",
                        "From": {"id": user["User_id"]}
                    }
                    print("Posting", payload)
                    requests.post(self.host, json=payload, headers={"Content-Type": "application/json"})

                else:
                    random.shuffle(courses)
                    found = False
                    for course in courses:
                        if course["topic"] in interest or course["subTopic"] in interest:
                            payload = {
                                "Text": course["subTopic"] + "$" + course["subTopicArabic"] + "$" + course["topic"] + "$" + course["topicArabic"],
                                "From": {"id": user["User_id"]}
                            }
                            found = True

                    # if none of the courses match the user interests then pass the failure payload to the bot
                    if not found:
                        payload = {
                            "Text": "fail",
                            "From": {"id": user["User_id"]}
                        }
                    print("Posting", payload)
                    requests.post(self.host, json=payload, headers={"Content-Type": "application/json"})


            elif user["lastNotified"] < user["Notification"]:
                self.user_col.update({"_id": user["_id"]}, {"$inc": {"lastNotified": 1}})

    def getnewCourses(self):
        course_len = 0
        timeout = 0
        while course_len == 0 and timeout <= 10:
            past = datetime.datetime.utcnow() - datetime.timedelta(days=7)
            courses = self.course_col.find({"lastUpdated": {"$gt": past.isoformat()}})
            print("courses", courses.count())
            # return courses that have been added in the past 4 weeks
            timeout += 1
            course_len = courses.count()

        print("returning courses")
        return courses
