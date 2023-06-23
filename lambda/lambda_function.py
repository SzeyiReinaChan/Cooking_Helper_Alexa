# -*- coding: utf-8 -*-

# This sample demonstrates handling intents from an Alexa skill using the Alexa Skills Kit SDK for Python.
# Please visit https://alexa.design/cookbook for additional examples on implementing slots, dialog management,
# session persistence, api calls, and more.
# This sample is built using the handler classes approach in skill builder.
import logging
import ask_sdk_core.utils as ask_utils

from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.dispatch_components import AbstractExceptionHandler
from ask_sdk_core.handler_input import HandlerInput

from ask_sdk_model import Response

import os 
import openai
import time
from dotenv import load_dotenv

import json
import gspread

load_dotenv()
# ==== configure OpenAI ====
openai.api_key = os.getenv("OPENAI_API_KEY")

CREAMY_MISO_GARLIC_PRAWN_LINGUINE= """
The ingredients for Creamy Miso Garlic Prawn Linguine for 4 person are follow. 
500g (1 lb) spaghetti
2 tbsp extra virgin olive oil
80g (3 oz) unsalted butter
600g (1 lb 5 oz) peeled & deveined prawns
4 garlic cloves, finely chopped
1 tsp shiro miso paste
½ cup white wine
juice of half a lemon
finely grated parmesan, to serve

Here are the steps:
Step 1: Combine the parsley and coriander in a small bowl and set aside.

For the next step of making lemon panko pangrattato, the ingredients for 4 person are\
below:
2 tbsp extra virgin olive oil
½ cup panko breadcrumbs*
1 tsp sea salt
3 tbsp finely chopped parsley
3 tbsp finely chopped coriander
zest of 1 lemon

Step 2: To make the lemon panko pangrattato, heat the olive oil in a frying pan over \
high heat. Add the panko breadcrumbs and salt, and toss for 2–3 minutes or until golden. \
Stir through 2 tablespoons each of the parsley and coriander (reserve the rest for later), \
plus the lemon zest.
Step 3: Bring a large pot of heavily salted water to the boil. While it’s coming to a boil,\
heat a large frying pan over a medium-high heat.
Step 4:Once the water is boiling, add the linguine. As the pasta cooks, place the oil and \
butter in the preheated pan. Before all the butter has melted, add the garlic and cook for \
half a minute until fragrant – you just want it to soften rather than brown.
Step 5:Now add the miso paste and use a whisk to stir it into the butter and oil until it’s \
well incorporated. Next, add the prawns and toss in the mixture for a minute. Add the wine and \
lemon juice and keep tossing the prawns in the mixture for another minute or until everything \
is well combined and looks creamy. Turn the heat off and wait for the pasta.
Step 6:Once the pasta is just al dente, scoop out a cup of pasta cooking liquid and set aside.\
Transfer the linguine into the prawn and sauce mixture using tongs and turn the heat up to high.
Step 7: Mix and toss the pasta in the sauce. Then add half a cup of the pasta cooking liquid \
and continue tossing and mixing for 3–4 minutes or until the sauce has thickened and is creamy\
and glossy. Toss through the remaining coriander and parsley. Remove from heat and divide among\
serving bowls. Sprinkle with parmesan and the lemon panko pangrattato and serve immediately.

"""

INSTRUCTIONS = f"""
Your task is to help user to make one of the dishes listed below.
Respond user questions based on the recipe delimited by triple backticks, respond user in at most 30 words.
Please aim to be as helpful, creative, friendly, and educative as possible in all of your responses.
Only output strictly realted to the question, with nothing else.
Every respond should be in complete sentence.
Do not use any external URLs in your responses.
Recipe = \'\'\'{CREAMY_MISO_GARLIC_PRAWN_LINGUINE}\'\'\'
"""


TEMPERATURE = 1
MAX_TOKENS = 128
FREQUENCY_PENALTY = 0
PRESENCE_PENALTY = 0.2

MAX_CONTEXT_QUESTIONS = 5

CHAT_HISTORY = []

sheet_url = "https://docs.google.com/spreadsheets/d/1WHhMP3BVUPYAkrLd6dVFwWQ9QlDAeOYRidMxwWebN9o/"
gc = gspread.service_account(filename = 'credentials.json')
sh = gc.open_by_url(sheet_url)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class LaunchRequestHandler(AbstractRequestHandler):
    """Handler for Skill Launch."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool

        return ask_utils.is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "Welcome to the cooking helper. This assistant will help you on making creamy miso garlic prawn linguine.\
        How can I help?"
        
        worksheet = sh.get_worksheet(0)
        # worksheet.clear()
        worksheet.update("A1", "User Questions")   # this function writes to a cell in the spreadsheet
        worksheet.update("B1", "VA responses")
        
        user_questions = worksheet.col_values(1)
        va_responses = worksheet.col_values(2)
        for i in range(1, len(user_questions)):
            CHAT_HISTORY.append((user_questions[i], va_responses[i]))

        
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )


# class HelloWorldIntentHandler(AbstractRequestHandler):
#     """Handler for Hello World Intent."""
#     def can_handle(self, handler_input):
#         # type: (HandlerInput) -> bool
#         return ask_utils.is_intent_name("HelloWorldIntent")(handler_input)

#     def handle(self, handler_input):
#         # type: (HandlerInput) -> Response
#         speak_output = "Hello World!"

#         return (
#             handler_input.response_builder
#                 .speak(speak_output)
#                 # .ask("add a reprompt if you want to keep the session open for the user to respond")
#                 .response
#         )



class AskChatGPTIntentHandler(AbstractRequestHandler):
    """Handler for Hello World Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AskChatGPTIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        # speak_output = "Activated Chat G P T Intent"
        
        new_question = handler_input.request_envelope.request.intent.slots["question"].value
        
        messages = [
            { "role": "system", "content": INSTRUCTIONS },
        ]
        
        for question, answer in CHAT_HISTORY[-MAX_CONTEXT_QUESTIONS:]:
            messages.append({ "role": "user", "content": question })
            messages.append({ "role": "assistant", "content": answer })
            
        messages.append({ "role": "user", "content": new_question })
        
        completion = ''
        
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            top_p=1,
            frequency_penalty=FREQUENCY_PENALTY,
            presence_penalty=PRESENCE_PENALTY,
        )
        
        while completion == '':
            time.sleep(3)

        response = completion.choices[0].message.content
        
        CHAT_HISTORY.append((new_question, completion.choices[0].message.content))
        
        worksheet = sh.get_worksheet(0)
        chat_history_filtered = list(filter(lambda x: not None, worksheet.col_values(1)))
        new_index = str(len(chat_history_filtered) + 1)
        worksheet.update("A" + new_index, new_question)   # this function writes to a cell in the spreadsheet
        worksheet.update("B" + new_index, completion.choices[0].message.content)

        return (
            handler_input.response_builder
                .speak(response)
                .ask('Is there anything else i can help you?')
                # .ask("add a reprompt if you want to keep the session open for the user to respond")
                .response
        )

class HelpIntentHandler(AbstractRequestHandler):
    """Handler for Help Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "You can say hello to me! How can I help?"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )


class CancelOrStopIntentHandler(AbstractRequestHandler):
    """Single handler for Cancel and Stop Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return (ask_utils.is_intent_name("AMAZON.CancelIntent")(handler_input) or
                ask_utils.is_intent_name("AMAZON.StopIntent")(handler_input))

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "Goodbye!"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .response
        )

class FallbackIntentHandler(AbstractRequestHandler):
    """Single handler for Fallback Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.FallbackIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In FallbackIntentHandler")
        speech = "Hmm, I'm not sure. You can say Hello or Help. What would you like to do?"
        reprompt = "I didn't catch that. What can I help you with?"

        return handler_input.response_builder.speak(speech).ask(reprompt).response

class SessionEndedRequestHandler(AbstractRequestHandler):
    """Handler for Session End."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response

        # Any cleanup logic goes here.

        return handler_input.response_builder.response


class IntentReflectorHandler(AbstractRequestHandler):
    """The intent reflector is used for interaction model testing and debugging.
    It will simply repeat the intent the user said. You can create custom handlers
    for your intents by defining them above, then also adding them to the request
    handler chain below.
    """
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("IntentRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        intent_name = ask_utils.get_intent_name(handler_input)
        speak_output = "You just triggered " + intent_name + "."

        return (
            handler_input.response_builder
                .speak(speak_output)
                # .ask("add a reprompt if you want to keep the session open for the user to respond")
                .response
        )


class CatchAllExceptionHandler(AbstractExceptionHandler):
    """Generic error handling to capture any syntax or routing errors. If you receive an error
    stating the request handler chain is not found, you have not implemented a handler for
    the intent being invoked or included it in the skill builder below.
    """
    def can_handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> bool
        return True

    def handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> Response
        logger.error(exception, exc_info=True)

        speak_output = "Sorry, I had trouble doing what you asked. Please try again."

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

# The SkillBuilder object acts as the entry point for your skill, routing all request and response
# payloads to the handlers above. Make sure any new handlers or interceptors you've
# defined are included below. The order matters - they're processed top to bottom.


sb = SkillBuilder()

sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(AskChatGPTIntentHandler())
# sb.add_request_handler(HelloWorldIntentHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(FallbackIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_request_handler(IntentReflectorHandler()) # make sure IntentReflectorHandler is last so it doesn't override your custom intent handlers

sb.add_exception_handler(CatchAllExceptionHandler())

lambda_handler = sb.lambda_handler()
