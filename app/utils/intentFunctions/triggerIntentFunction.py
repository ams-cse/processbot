import sys
from app.utils.intentFunctions import process_names, process_run
from app.utils import responseHelper

# Mapt alle Intents einer entsprechenden Intent-Funktion
intentDict = {
    "process_names": process_names,
    "process_run": process_run
}

# Führt die jeweiligen Intent-Funktion zum Intent aus
# Input: response (dialogflow)
# Ouput: ResponseObject
def run(dialogflowResponse):
    intentDisplayName = dialogflowResponse.query_result.intent.display_name
    # print(name)
    if intentDisplayName in intentDict:
        # print("intent exists")
        return intentDict.get(intentDisplayName).run(dialogflowResponse)
    else:
        # print("intent doesn't exists in intentDict")
        return responseHelper.createResponseObject([dialogflowResponse.query_result.fulfillment_text],[], "", "")

