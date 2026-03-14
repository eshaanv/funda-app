.PHONY: deploy

CLOUD_RUN_FLAGS ?= --no-invoker-iam-check

deploy: push-image
	gcloud run deploy "$(SERVICE_NAME)" \
		--image "$(IMAGE)" \
		--region "$(REGION)" \
		--project "$(PROJECT_ID)" \
		--platform managed $(CLOUD_RUN_FLAGS)
