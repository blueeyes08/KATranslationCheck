#!/bin/sh
echo "Backupping DE"
gcloud beta datastore export --namespaces="de" gs://katc-datastorage-backup-1
echo "Backupping sv-SE"
gcloud beta datastore export --namespaces="sv-SE" gs://katc-datastorage-backup-1
echo "Backupping ru"
gcloud beta datastore export --namespaces="ru" gs://katc-datastorage-backup-1
echo "Backupping pl"
gcloud beta datastore export --namespaces="pl" gs://katc-datastorage-backup-1
echo "Backupping cs"
gcloud beta datastore export --namespaces="cs" gs://katc-datastorage-backup-1
