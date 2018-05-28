#!/bin/sh
echo "Backupping de"
gcloud beta datastore export --namespaces="de" gs://katc-datastorage-backup-1
echo "Backupping sv-SE"
gcloud beta datastore export --namespaces="sv-SE" gs://katc-datastorage-backup-1
echo "Backupping ru"
gcloud beta datastore export --namespaces="ru" gs://katc-datastorage-backup-1
echo "Backupping pl"
gcloud beta datastore export --namespaces="pl" gs://katc-datastorage-backup-1
echo "Backupping cs"
gcloud beta datastore export --namespaces="cs" gs://katc-datastorage-backup-1
echo "Backupping sr"
gcloud beta datastore export --namespaces="sr" gs://katc-datastorage-backup-1
echo "Backupping da"
gcloud beta datastore export --namespaces="da" gs://katc-datastorage-backup-1
echo "Backupping pt-PT"
gcloud beta datastore export --namespaces="pt-PT" gs://katc-datastorage-backup-1
echo "Backupping nb"
cloud beta datastore export --namespaces="nb" gs://katc-datastorage-backup-1
