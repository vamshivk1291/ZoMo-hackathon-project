# -*- coding: utf-8 -*-

# This sample demonstrates handling intents from an Alexa skill using the Alexa Skills Kit SDK for Python.
# Please visit https://alexa.design/cookbook for additional examples on implementing slots, dialog management,
# session persistence, api calls, and more.
# This sample is built using the handler classes approach in skill builder.
import logging
import ask_sdk_core.utils as ask_utils
import os
import io
import calendar
import boto3
import json
import pandas as pd
import requests
import random

from ask_sdk.standard import StandardSkillBuilder
from ask_sdk_dynamodb.adapter import DynamoDbAdapter
from ask_sdk_core.dispatch_components import AbstractRequestInterceptor
from ask_sdk_core.dispatch_components import AbstractResponseInterceptor

from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.dispatch_components import AbstractExceptionHandler
from ask_sdk_core.handler_input import HandlerInput

from ask_sdk_model import Response

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class LaunchRequestHandler(AbstractRequestHandler):
    """Handler for Skill Launch."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool

        return ask_utils.is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        
        # fetching the device id from the request envelope to use the correct greeting based on time zone
        device_id = handler_input.request_envelope.context.system.device.device_id

        user_time_zone = ""
        greeting = ""

        # making the API call
        # user_preferences_client is used to call get_system_time_zone, which returns an ISO time zone
        try:
            user_preferences_client = handler_input.service_client_factory.get_ups_service()
            user_time_zone = user_preferences_client.get_system_time_zone(device_id)
        except Exception as e:
            user_time_zone = 'error.'
            logger.error(e)

        if user_time_zone == 'error':
            greeting = 'Hello.'
        else:
            # get the hour of the day or night in your customer's time zone
            from utils import get_hour
            hour = get_hour(user_time_zone)
            if 0 <= hour and hour <= 4:
                greeting = "Hi night-owl!"
            elif 5 <= hour and hour <= 11:
                greeting = "Good morning!"
            elif 12 <= hour and hour <= 17:
                greeting = "Good afternoon!"
            elif 17 <= hour and hour <= 23:
                greeting = "Good evening!"
            else:
                greeting = "Howdy partner!"
        
        speak_output = ''
        session_attributes = handler_input.attributes_manager.session_attributes
        name = session_attributes["user_name"]
        session_attributes["greeting"] = greeting
        
        if session_attributes["visits"] == 0:
            speak_output = f"{greeting} Welcome to the Zomo Finder. "  \
                f"My name is Zomo,  what's yours?"
        else:
            speak_output = f"{greeting} {name}, Welcome back to the Zomo Finder. "  \
                f"What you wanna search for, new movie suggestion or zodiac?"
        
        # increment the number of visits and save the session attributes so the
        # ResponseInterceptor will save it persistently.
        session_attributes["visits"] = session_attributes["visits"] + 1

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )


class CaptureNameIntentHandler(AbstractRequestHandler):
    """Handler for Skill Launch."""
    # can_handle - If your skill receives a request, can_handle() function within each handler determines whether or not that handler can service the request
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return (
            # this checks whether the request is INTENT request not the LAUNCH request and then checks if the INTENT name is CaptureInitialsIntent
            ask_utils.is_request_type("IntentRequest")(handler_input) and ask_utils.is_intent_name("CaptureNameIntent")(handler_input)
        )

    def handle(self, handler_input):
        # handle function returns a response to the user
        # type: (HandlerInput) -> Response
        
        speak_output = ''
        
        # get the current session attributes, creating an object you can read/update
        session_attributes = handler_input.attributes_manager.session_attributes
        
        # Get the slot values
        name = ask_utils.request_util.get_slot(handler_input, "name").value
        #category = ask_utils.request_util.get_slot(handler_input, "category").value
        
        greeting = session_attributes["greeting"]
        session_attributes["user_name"] = name
        
        speak_output = f"{greeting} {name}. " \
                f"What you wanna search for, new movie suggestion or zodiac?"
        
        # store all the updated session data
        handler_input.attributes_manager.session_attributes = session_attributes
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )


class CaptureCategoryIntentHandler(AbstractRequestHandler):
    """Handler for Skill Launch."""
    # can_handle - If your skill receives a request, can_handle() function within each handler determines whether or not that handler can service the request
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return (
            # this checks whether the request is INTENT request not the LAUNCH request and then checks if the INTENT name is CaptureCategoryIntent
            ask_utils.is_request_type("IntentRequest")(handler_input) and ask_utils.is_intent_name("CaptureCategoryIntent")(handler_input)
        )

    def handle(self, handler_input):
        # handle function returns a response to the user
        # type: (HandlerInput) -> Response
        
        speak_output = ''
        
        # get the current session attributes, creating an object you can read/update
        session_attributes = handler_input.attributes_manager.session_attributes
        
        # Get the slot values
        category = ask_utils.request_util.get_slot(handler_input, "category").value
        
        session_attributes["user_category"] = category
        name = session_attributes["user_name"]
        
        if category.lower() == 'zodiac': 
            speak_output = f"Great {name}. Tell me your birth date? "
        elif category.lower() == 'movie':
            speak_output = f"Great {name}. Tell me your preferences. Is it specific Language, Actor or Genre? "
        else:
            speak_output = f"Choose from 'Movie' or 'Zodiac sign'"
        
        # store all the updated session data
        handler_input.attributes_manager.session_attributes = session_attributes
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )


class CaptureZodiacIntentHandler(AbstractRequestHandler):
    """Handler for Skill Launch."""
    # can_handle - If your skill receives a request, can_handle() function within each handler determines whether or not that handler can service the request
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return (
            # this checks whether the request is INTENT request not the LAUNCH request and then checks if the INTENT name is CaptureZodiacIntent
            ask_utils.is_request_type("IntentRequest")(handler_input) and ask_utils.is_intent_name("CaptureZodiacIntent")(handler_input)
        )

    def filter(self, X):
        date = X.split()
        month = date[0]
        month_as_index = list(calendar.month_abbr).index(month[:3].title())
        day = int(date[1])
        return (month_as_index, day)

    def handle(self, handler_input):
        # handle function returns a response to the user
        # type: (HandlerInput) -> Response
        
        speak_output = ''
        
        # get the current session attributes, creating an object you can read/update
        session_attributes = handler_input.attributes_manager.session_attributes
        
        # Get the slot values
        day = ask_utils.request_util.get_slot(handler_input, "day").value
        month = ask_utils.request_util.get_slot(handler_input, "month").value
        year = ask_utils.request_util.get_slot(handler_input, "year").value
        
        session_attributes["day"] = day
        session_attributes["month"] = month
        session_attributes["year"] = year
        name = session_attributes["user_name"]
        
        url = f"https://docs.google.com/spreadsheets/d/e/" \
        f"2PACX-1vRew2hY5IvEH6Zk4ZzRktRBt_bHADehZQtDTtyuqVmofn5Ekqu9mZoYdiZfHztGZcNuOEtIJWflhuYL/pub?gid=1951203344&single=true&output=csv"
        csv_content = requests.get(url).content
        df = pd.read_csv(io.StringIO(csv_content.decode('utf-8')))
        zodiac = ""
        month_as_index = list(calendar.month_abbr).index(month[:3].title())
        usr_dob = (month_as_index, int(day))
        for index, row in df.iterrows():
            if self.filter(row['Start']) <= usr_dob <= self.filter(row['End']):
                zodiac = row['Zodiac']
        
        session_attributes["user_zodiac"] = zodiac
        
        speak_output = f"I see you were born on the {month} {day}, which means that your zodiac sign will be {zodiac}. "
        
        # store all the updated session data
        handler_input.attributes_manager.session_attributes = session_attributes
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )


class CaptureMovieIntentHandler(AbstractRequestHandler):
    """Handler for Skill Launch."""
    # can_handle - If your skill receives a request, can_handle() function within each handler determines whether or not that handler can service the request
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return (
            # this checks whether the request is INTENT request not the LAUNCH request and then checks if the INTENT name is CaptureMovieIntent
            ask_utils.is_request_type("IntentRequest")(handler_input) and ask_utils.is_intent_name("CaptureMovieIntent")(handler_input)
        )

    def filter(self, df, language=None, actor=None, genre=None):
        if language and actor and genre:
            df_filtered = df[(df['Language'].str.contains(language)) & (df['Actor'].str.contains(actor)) & (df['Genre'].str.contains(genre))] 
        elif actor and genre:
            df_filtered = df[(df['Actor'].str.contains(actor)) & (df['Genre'].str.contains(genre))]
        elif language and actor:
            df_filtered = df[(df['Language'].str.contains(language)) & (df['Actor'].str.contains(actor))]
        elif language and genre:
            df_filtered = df[(df['Language'].str.contains(language)) & (df['Genre'].str.contains(genre))]
        elif actor:
            df_filtered = df[(df['Actor'].str.contains(actor))]
        elif genre:
            df_filtered = df[(df['Genre'].str.contains(genre))]
        elif language:
            df_filtered = df[(df['Language'].str.contains(language))]
        else:
            df_filtered = df   
        return df_filtered

    def handle(self, handler_input):
        # handle function returns a response to the user
        # type: (HandlerInput) -> Response
        
        speak_output = ""
        language=None
        actor=None
        genre=None
        
        # get the current session attributes, creating an object you can read/update
        session_attributes = handler_input.attributes_manager.session_attributes
        
        # Get the slot values
        
        try:
            language = ask_utils.request_util.get_slot(handler_input, "language").value
            language = language.replace(" ", "").lower()[:4]
        except:
            pass
        try:
            actor = ask_utils.request_util.get_slot(handler_input, "actor").value
            actor = actor.replace(" ", "").lower()[:4]
        except:
            pass
        try:
            genre = ask_utils.request_util.get_slot(handler_input, "genre").value
            genre = genre.replace(" ", "").lower()[:4]
        except:
            pass
        
        name = session_attributes["user_name"]
        
        url = f"https://docs.google.com/spreadsheets/d/e/2PACX-1vS806tlz5WcANdWbwI8bmk5sWFn8B3KQ0Oj2SXY1JCOxqS6u7eZX9LXhNU1o7wDaA/pub?gid=905238258&single=true&output=csv"
        csv_content = requests.get(url).content
        df = pd.read_csv(io.StringIO(csv_content.decode('utf-8')))
        movie = ""
        X = self.filter(df, language=language, actor=actor, genre=genre)
        if len(X) != 0:
            i = int(random.randint(0,len(X)-1))
            print(i)
            movie = X.iloc[i,3]
        
        session_attributes["user_movie"] = movie
        
        speak_output = f"I would like to suggest {movie}, based on your preferences. Happy watching !! "
        
        # store all the updated session data
        handler_input.attributes_manager.session_attributes = session_attributes
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
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

# For persistence attribute
class LoadDataInterceptor(AbstractRequestInterceptor):
    """Check if user is invoking skill for first time and initialize preset."""
    def process(self, handler_input):
        # type: (HandlerInput) -> None
        persistent_attributes = handler_input.attributes_manager.persistent_attributes
        session_attributes = handler_input.attributes_manager.session_attributes

        # ensure important variables are initialized so they're used more easily in handlers.
        # This makes sure they're ready to go and makes the handler code a little more readable

        if 'user_name' not in persistent_attributes:
            persistent_attributes["user_name"] = ""

        if 'user_name' not in session_attributes:
            session_attributes["user_name"] = ""

        # if you're tracking user_name between sessions, use the persistent value
        # set the visits value (either 0 for new, or the persistent value)
        session_attributes["user_name"] = persistent_attributes["user_name"] if 'user_name' in persistent_attributes else ""
        session_attributes["visits"] = persistent_attributes["visits"] if 'visits' in persistent_attributes else 0


# For persistence attribute
class LoggingRequestInterceptor(AbstractRequestInterceptor):
    """Log the alexa requests."""
    def process(self, handler_input):
        # type: (HandlerInput) -> None
        logger.debug('----- REQUEST -----')
        logger.debug("{}".format(
            handler_input.request_envelope.request))
        
# For persistence attribute  
class SaveDataInterceptor(AbstractResponseInterceptor):
    """Save persistence attributes before sending response to user."""
    def process(self, handler_input, response):
        # type: (HandlerInput, Response) -> None
        persistent_attributes = handler_input.attributes_manager.persistent_attributes
        session_attributes = handler_input.attributes_manager.session_attributes

        persistent_attributes["user_name"] = session_attributes["user_name"]
        persistent_attributes["visits"] = session_attributes["visits"]

        handler_input.attributes_manager.save_persistent_attributes()


# For persistence attribute
class LoggingResponseInterceptor(AbstractResponseInterceptor):
    """Log the alexa responses."""
    def process(self, handler_input, response):
        # type: (HandlerInput, Response) -> None
        logger.debug('----- RESPONSE -----')
        logger.debug("{}".format(response))


# The SkillBuilder object acts as the entry point for your skill, routing all request and response
# payloads to the handlers above. Make sure any new handlers or interceptors you've
# defined are included below. The order matters - they're processed top to bottom.


# With persistence attribute
sb = StandardSkillBuilder(table_name=os.environ.get("DYNAMODB_PERSISTENCE_TABLE_NAME"), auto_create_table=False)

sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(CaptureNameIntentHandler())
sb.add_request_handler(CaptureCategoryIntentHandler())
sb.add_request_handler(CaptureZodiacIntentHandler())
sb.add_request_handler(CaptureMovieIntentHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(FallbackIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_request_handler(IntentReflectorHandler()) # make sure IntentReflectorHandler is last so it doesn't override your custom intent handlers

sb.add_exception_handler(CatchAllExceptionHandler())

# Interceptors - For Persistence Attributes
# they runs - before running through the request handlers
sb.add_global_request_interceptor(LoadDataInterceptor())
sb.add_global_request_interceptor(LoggingRequestInterceptor())
# they runs - after chosen request handler returns its result
sb.add_global_response_interceptor(SaveDataInterceptor())
sb.add_global_response_interceptor(LoggingResponseInterceptor())

lambda_handler = sb.lambda_handler()