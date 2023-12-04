#!/bin/bash
bot_pid_file="bot_pid.txt"
scheduler_pid_file="scheduler_pid.txt"
bot_pid=`cat $bot_pid_file`
scheduler_pid=`cat $scheduler_pid_file`
cp /dev/null $bot_pid_file
cp /dev/null $scheduler_pid_file
source venv/bin/activate
nohup python main.py &
echo $! >> $bot_pid_file
nohup python scheduler.py &
echo $! >> $scheduler_pid_file
kill $bot_pid
kill $scheduler_pid