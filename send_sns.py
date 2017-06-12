#!/usr/bin/env python

# This python script allows any application to send sns alerts to any topic
# Make sure you create the topic though!
# Usage: printf <msg> | sms_notify.py --topic=<topic> --sub=<sub>

import boto3
import sys
import logging
import time
import tornado.options
import subprocess
import string
import os


rate_limit_threshold = 5 #no. of messages
rate_limit_secs = 60 #in how many secs?
# To explain the above 2 parameters, rate_limit_threshold messages will be allowed
# to be sent in rate_limit_secs.

# The following message will be sent when the theshold is reached
suppress_msg = "**PROBLEM** Passed the notification threshold. There are more problems than has been paged to you. Please check nagios NOW!"


def rate_limit(sns, arn, msg, sub):

    curr_time = int(time.time())

    # get last five alerts sent out
    time_rate_bash_command = "cat /var/log/nagios/nagios.log | grep " + tornado.options.options.topic + " | awk -F \" \" '{print $1}' | tr -d \"[]\" | tail -n "+ str(rate_limit_threshold)
    time_rate_bash_output = subprocess.check_output(time_rate_bash_command, shell=True)

    #make sure that 5 alerts actually exist in the logs
    count = string.count(time_rate_bash_output, "\n")
        
    #lock file when threshold has been passed
    snslock = "/tmp/" + tornado.options.options.topic + ".snslock"
    
    #make sure there are actually more than 5 alerts in the log
    if count >= rate_limit_threshold:
        #get the 5th from current alert
        time_rate = int(time_rate_bash_output.split('\n')[0])
        if curr_time - time_rate > rate_limit_secs:
            response = sns.publish(arn, msg, sub)
            logging.info(response)
            # clear the lock file
            if os.path.exists(snslock):
                os.remove(snslock)
        else:
            # if lock file exists dont text supress message
            if os.path.exists(snslock):
                logging.warn(tornado.options.options.topic + ":" + suppress_msg)
            else:
                print sns.publish(arn, suppress_msg, sub)
                logging.warn(tornado.options.options.topic + ":" + suppress_msg)
                open(snslock, 'a').close()
                os.utime(snslock, None)
    else:
        logging.info(sns.publish(arn, msg, sub))
        
    

def send_sns(topic, msg, sub):

    sns = boto3.client('sns')

    arn = ""
    for topics in sns.get_all_topics()["ListTopicsResponse"]["ListTopicsResult"]["Topics"]:
        if topic in topics["TopicArn"]:
            arn = topics["TopicArn"]
        
    if arn == "":
        logging.error("topic not found!")
        exit(0)
    
    if tornado.options.options.rate_limit == True:
        rate_limit(sns, arn, msg, sub)   
    else:
        print sns.publish(arn, msg, sub)


def send_text(number, msg, sub):
    """
    Sends a notification to a phone number, and not to a topic.

    This is useful if your notifications are more dynamic.
    """

    sns = boto3.client('sns')
    if tornado.options.options.rate_limit == True:
        # The ratelimit function needs changes to support this
        raise NotImplementedError
    else:
        print sns.publish(PhoneNumber=number, Message=msg)


def get_msg():
    msg = ""
    
    #message is piped in
    for line in sys.stdin.readlines():
        msg = msg + "\n" + line
        
    #sns will throw a bad argument error for an empty body but is happy with a blank line
    if msg == "":
        msg = "\n"

    return msg

def main():    
    tornado.options.define("number", help="specify the destination phone number", default="", type=str)
    tornado.options.define("topic", help="specify the destination topic", default="", type=str)
    tornado.options.define("sub", help="specify the subject of the message", default="", type=str)
    tornado.options.define("rate_limit", help="use this to run in rate limited mode. DEFAULT=False", default=False, type=bool)    
    tornado.options.define("region", help="specify the AWS region to use", default="us-east-1", type=str)
    tornado.options.parse_command_line()
    
    if tornado.options.options.topic == "":
        if tornado.options.options.number == "":
            logging.error("No topic or phone number specified. use --topic or --number or look at --help for more info.")
            exit(0)
        else:
            # Phone number, but no topic
            msg = get_msg()
            number = tornado.options.options.number
            if '@' in number:
               number = number.split('@')[0]
            if len(number) == 10:
               number = '1' + number
            send_text(number, msg, tornado.options.options.sub)
    else:
        # topic specified
        if tornado.options.options.number != "":
            logging.warning("Both topic and phone number specified. Notifying the topic. See --help for more info.")
        msg = get_msg()
        send_sns(tornado.options.options.topic, msg, tornado.options.options.sub)
    
if __name__ == "__main__":
    main()
