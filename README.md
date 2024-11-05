# 動画検索システムハンズオン

## How to start

cd ~/movie_search/backend

gcloud builds submit --tag gcr.io/minitap-genai-app-dev-handson/backend
gcloud run deploy backend --image gcr.io/minitap-genai-app-dev-handson/backend --region asia-northeast1 --no-allow-unauthenticated 

--service-account 608635780090-compute@developer.gserviceaccount.com

cd ~/movie_search/frontend

gcloud builds submit --tag gcr.io/minitap-genai-app-dev-handson/frontend
gcloud run deploy frontend --image gcr.io/minitap-genai-app-dev-handson/frontend --region asia-northeast1 --allow-unauthenticated 

--service-account frontend-service-account@minitap-genai-app-dev-handson.iam.gserviceaccount.com
