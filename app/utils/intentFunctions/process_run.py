# pylint: disable=no-member
import json
from google.protobuf.json_format import MessageToJson
from app.models import Process, Edge, GeneralInstruction, DetailInstruction, SplitQuestion, Node, ButtonName
from app.utils import responseHelper, dialogflowHelper
from app.utils import buttons as buttons
from app import db

# Weg: man kommt hier her über submit_message(JS) --> send_userText(PY Route)
def run(dialogflowResponse):
    parameters_json = json.loads(MessageToJson(dialogflowResponse.query_result.parameters))
    processName = parameters_json['process_name_parameter']

    try:
        # Aktuellen Prozess holen
        process = Process.query.filter_by(processName=processName).first()
        processId = process.id
    except: #Kein Prozess angegeben, bzw. Prozess nicht gefunden --> alle Prozesse als Button anzeigen
        message1 = dialogflowResponse.query_result.fulfillment_text
        message2 = "These are the processes I can help you with:"
        runButtons = []
        for process in Process.query.all():
            button = buttons.createCustomButton(process.processName,"process_run", process.processName)
            runButtons.append(button)
        runButtons.extend(buttons.CANCEL_RUN_BUTTON)
        messages = [message1, message2]
        return responseHelper.createResponseObject(messages,runButtons,"","","","")
    
    # falls Process zuvor abgebrochen wurde, frage ob an dieser Stelle fortfahren werden soll
    try:
        currentStepNode = Node.query.filter_by(currentStep = True).filter_by(processId = processId).first()
        message1 = "I have detected, that you have started this process before. Do you want to resume your last state?"
        return responseHelper.createResponseObject([message1],buttons.RESUME_RUN_BUTTONS,processId,processName,currentStepNode.id,"")
    
    except: # wenn nicht starte von vorne    
        # erste Aktivität im Prozess nehmen
        firstActivityId = Edge.query.filter(Edge.sourceId.like('StartEvent_%')).filter_by(processId=process.id).first().targetId
        previousStepId = Edge.query.filter(Edge.processId == process.id).filter(Edge.targetId == firstActivityId).first().sourceId
        firstActivity = Node.query.filter_by(id = firstActivityId).first()

        if(firstActivity.type == "exclusiveGateway"):
            try:
                splitQuestion = SplitQuestion.query.filter_by(nodeId=firstActivityId).first().text
            except:  # Falls es dafür keine Splitquestion gibt, dann handelt es sich um einen Join-Gateway --> Dann nächster Knoten ignorieren
                message = "You have reached a join gateway, press \"Yes\" to continue."
                messages = [message]
                return responseHelper.createResponseObject(messages, buttons.REDUCED_RUN_BUTTONS, processId, processName, firstActivityId, previousStepId)
                    
            # Splitquestion und Buttons ausgeben
            optionEdges = Edge.query.filter(Edge.sourceId == firstActivityId).filter_by(processId=processId)
            optionButtons = []
            for edge in optionEdges:
                eventId = edge.targetId
                buttonName = ButtonName.query.filter_by(nodeId=eventId).first().text
                optionButton = buttons.createCustomButton(buttonName,"process_run",eventId) # zB.: "process_run$customButton$IntermediateThrowEvent_1szmt2n"
                optionButtons.append(optionButton)
            optionButtons.extend(buttons.CANCEL_RUN_BUTTON) 
            return responseHelper.createResponseObject([splitQuestion], optionButtons, processId, processName, firstActivityId ,previousStepId)

        elif(firstActivity.type == "task"):
            message1 = dialogflowResponse.query_result.fulfillment_text # Okay, let's start process "Entity".
            message2 = GeneralInstruction.query.filter_by(nodeId=firstActivityId).first().text # Generelle Anweisungen für ersten Schritt
            message3 = "When you are done press \"Yes\", should you need further assistance press \"Help\"."
            messages = [message1, message2, message3]
            
            currentProcess = processId
            currentProcessName = processName
            currentProcessStep = firstActivityId
            previousProcessStep = previousStepId

            return responseHelper.createResponseObject(messages, buttons.STANDARD_RUN_BUTTONS,currentProcess, currentProcessName, currentProcessStep,previousProcessStep)

        else: #Intermediate Throw Event?
            pass #dürfte nicht vorkommen
       

# Weg: man kommt hier her über submit_button(JS) --> send_button(PY Route) --> triggerButtonFunction (ButtonDict)
def button_run(pressedButtonValue, currentProcess, currentProcessName, currentProcessStep, previousProcessStep):

    # Aktueller Prozesslauf abrechen
    if pressedButtonValue == "process_run_cancel":
        try:
            processName = Process.query.filter_by(id=currentProcess).first().processName
            message1 = "Okay, the current process instance of process \"" + processName + "\" will be canceled."
            message2 = "Your state will be saved for later."
            node = Node.query.filter_by(id=currentProcessStep).filter_by(processId=currentProcess).first()
            node.currentStep = True
            db.session.commit()
            messages = [message1,message2]
        except: # kein Prozessname
            message = "Alright, the request will be canceled."
            messages = [message]
        return responseHelper.createResponseObject(messages,[],"","","","")    
    
    # Gebe die DetailInstruction aus
    elif pressedButtonValue == "process_run_help":      
        try:
            message = DetailInstruction.query.filter_by(nodeId=currentProcessStep).first().text # Detail Anweisungen für aktuellen Schritt
        except:
            message = "Sorry, I can't provide you any further help for this task."
        return responseHelper.createResponseObject([message],buttons.REDUCED_RUN_BUTTONS,currentProcess, currentProcessName, currentProcessStep, previousProcessStep)

     # Starte den Prozess von Vorne
    elif pressedButtonValue == "process_run_no":
        # currentStep in der Datenbank zurücksetzen
        currentStepNode = Node.query.filter_by(id = currentProcessStep).first()
        currentStepNode.currentStep = False
        db.session.commit()
        # von vorne starten
        dialogflowResponse = dialogflowHelper.detect_intent_texts("run process " + currentProcessName)
        return run(dialogflowResponse)

     # Starte den Prozess an dem letzten State
    elif pressedButtonValue == "process_run_resume":
        # currentStep in der Datenbank zurücksetzen
        currentStepNode = Node.query.filter_by(id = currentProcessStep).first()
        currentStepNode.currentStep = False
        db.session.commit()

        # Prozess an dieser Stelle weitermachen:
        # Falls dieser Node ein Gateway ist, stelle die Splitquestion
        if (currentStepNode.type == "exclusiveGateway"):
            try:
                splitQuestion = SplitQuestion.query.filter_by(nodeId=currentProcessStep).first().text
            except:  # Falls es dafür keine Splitquestion gibt, dann handelt es sich um einen Join-Gateway --> Dann nächster Knoten ignorieren
                message = "You have reached a join gateway, press \"Yes\" to continue."
                messages = [message]
                return responseHelper.createResponseObject(messages, buttons.REDUCED_RUN_BUTTONS, currentProcess, currentProcessName, currentProcessStep ,"")
                
            # Splitquestion und Buttons ausgeben
            optionEdges = Edge.query.filter(Edge.sourceId == currentProcessStep).filter_by(processId=currentProcess)
            optionButtons = []
            for edge in optionEdges:
                eventId = edge.targetId
                buttonName = ButtonName.query.filter_by(nodeId=eventId).first().text
                optionButton = buttons.createCustomButton(buttonName,"process_run",eventId) # zB.: "process_run$customButton$IntermediateThrowEvent_1szmt2n"
                optionButtons.append(optionButton)
            optionButtons.extend(buttons.CANCEL_RUN_BUTTON) 
            return responseHelper.createResponseObject([splitQuestion], optionButtons, currentProcess, currentProcessName, currentProcessStep ,"")

        # Wenn ein Fehler fliegt, dann gibt es keine Anweisung mehr für die Activity --> Ende erreicht
        try:
            message = GeneralInstruction.query.filter_by(nodeId=currentProcessStep).first().text # Generelle Anweisungen für den nächsten Schritt
        except:
            message = "You have successfully gone through the process \"" + currentProcessName + "\"."
            return responseHelper.createResponseObject([message], [], "", "", "", "")

        return responseHelper.createResponseObject([message], buttons.STANDARD_RUN_BUTTONS, currentProcess, currentProcessName, currentProcessStep, "")

    else: # Nächster Schritt --> "process_run_yes"
        nextNodeId = Edge.query.filter(Edge.sourceId == currentProcessStep).filter_by(processId=currentProcess).first().targetId
        nextNode = Node.query.filter_by(id=nextNodeId).first()
        
        # Falls dieser Node ein Gateway ist, stelle die Splitquestion
        if (nextNode.type == "exclusiveGateway"):
            try:
                splitQuestion = SplitQuestion.query.filter_by(nodeId=nextNodeId).first().text
            except:  # Falls es dafür keine Splitquestion gibt, dann handelt es sich um einen Join-Gateway --> Dann nächster Knoten ignorieren
                message1 = "You have reached a join gateway, press \"Yes\" to continue."
                return responseHelper.createResponseObject([message1], buttons.REDUCED_RUN_BUTTONS, currentProcess, currentProcessName, nextNodeId ,currentProcessStep)
                
            # Splitquestion und Buttons ausgeben
            optionEdges = Edge.query.filter(Edge.sourceId == nextNodeId).filter_by(processId=currentProcess)
            optionButtons = []
            for edge in optionEdges:
                eventId = edge.targetId
                buttonName = ButtonName.query.filter_by(nodeId=eventId).first().text
                optionButton = buttons.createCustomButton(buttonName,"process_run",eventId) # zB.: "process_run$customButton$IntermediateThrowEvent_1szmt2n"
                optionButtons.append(optionButton)
            optionButtons.extend(buttons.CANCEL_RUN_BUTTON) 
            return responseHelper.createResponseObject([splitQuestion], optionButtons, currentProcess, currentProcessName, nextNodeId ,currentProcessStep)

        # Wenn ein Fehler fliegt, dann gibt es keine Anweisung mehr für die Activity --> Ende erreicht
        try:
            message = GeneralInstruction.query.filter_by(nodeId=nextNodeId).first().text # Generelle Anweisungen für den nächsten Schritt
        except:
            print("End of process reached")
            processName = Process.query.filter_by(id=currentProcess).first().processName
            message = "You have successfully gone through the process \"" + processName + "\"."
            return responseHelper.createResponseObject([message], [], "", "", "", "")

        return responseHelper.createResponseObject([message], buttons.STANDARD_RUN_BUTTONS, currentProcess, currentProcessName, nextNodeId, currentProcessStep)

# Weg: man kommt hier her über submit_button(JS) --> send_button(PY Route) --> triggerButtonFunction (customButtonDict)
def customButton_run(pressedButtonValue, currentProcess, currentProcessName, currentProcessStep, previousProcessStep):
    # zB. CustomButtonValue = "process_run$customButton$Reisekosten"
    # zB.: "process_run$customButton$IntermediateThrowEvent_1szmt2n"

    # Wenn kein currentProcess da ist, dann sind die ProzessButtons eingeblendet, andernfalls ist man an einem Split-Gateway
    if (currentProcess == ""):
        entity = pressedButtonValue[25:]
        dialogflowResponse = dialogflowHelper.detect_intent_texts(entity)
        return run(dialogflowResponse)
    else:
        eventId = pressedButtonValue[25:]
        return button_run("process_run_yes",currentProcess, currentProcessName, eventId,currentProcessStep)
