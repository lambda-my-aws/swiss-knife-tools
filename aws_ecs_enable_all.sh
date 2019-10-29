#!/usr/bin/env bash

for setting in serviceLongArnFormat taskLongArnFormat containerInstanceLongArnFormat awsvpcTrunking containerInsights ;do
   aws ecs put-account-setting --name $setting --value enabled
done
