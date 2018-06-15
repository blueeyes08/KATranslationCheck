#!/bin/sh
gcloud beta datastore export --namespaces="de,sv-SE,ru,pl,cs,sr,da,pt-PT,nb,ka,ja,lt,hy-AM" gs://katc-datastorage-backup-1
