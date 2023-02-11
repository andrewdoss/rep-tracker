# -*- coding: utf-8 -*-

import csv
import io
import logging
import ask_sdk_core.utils as ask_utils

from ask_sdk_core.api_client import DefaultApiClient
from ask_sdk_core.skill_builder import CustomSkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.dispatch_components import AbstractExceptionHandler
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response
from ask_sdk_model.services.api_client_request import ApiClientRequest

import db_utils
import errors
import utils


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class LaunchRequestHandler(AbstractRequestHandler):
    """Handler for Skill Launch."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool

        return ask_utils.is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
            
        speak_output = "Welcome to Rep Tracker!"
        ask_output = "You can say track followed by a quantity and exercise " \
                       "name, or ask for your total reps for today."

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(ask_output)
                .response
        )


class CreateRepsIntentHandler(AbstractRequestHandler):
    """Handler for creating new reps."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("CreateRepsIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        quantity = ask_utils.request_util.get_slot(handler_input, "quantity").value
        exercise = ask_utils.request_util.get_slot(handler_input, "exercise").value
        
        device_timezone = utils.get_user_timezone(handler_input)
        hashed_device_id = utils.get_hashed_device_id(handler_input)
        
        try:
            db_utils.create_reps(quantity, exercise, hashed_device_id)
            speak_output = f"{quantity} {exercise} tracked."
        except errors.UnrecognizedExerciseError:
            speak_output = f"I'm sorry. I don't recognize the exercise {exercise}."
        ask_output = "Anything else?"
        
        # For now, very inefficiently write out the dataset for each insert
        # TODO: should probably wrap this in a try-catch so user doesn't retry insert
        # based on a failure to cache the daily aggregates to s3.
        object_name = f"{hashed_device_id}.csv"
        daily_reps = db_utils.get_daily_reps(
            hashed_device_id,
            device_timezone,
        )
        with io.StringIO() as f:
            writer = csv.writer(f)
            for row in daily_reps:
                writer.writerow(row)
            f.seek(0)
            utils.put_s3_object(
                object_name,
                f.read().encode(),
            )


        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(ask_output)
                .response
        )
        
        
class AggregateRepsIntentHandler(AbstractRequestHandler):
    """Handler for aggregating existing reps.
    
    Currently only returns reps for current day.
    
    TODO: return reps for other user-specified time ranges. 
    """
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AggregateRepsIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        device_timezone = utils.get_user_timezone(handler_input)
        hashed_device_id = utils.get_hashed_device_id(handler_input)
        reps = db_utils.get_todays_reps(
            hashed_device_id,
            device_timezone=device_timezone,
        )
        
        if not reps:
            speak_output = "You don't have any reps yet today."
        else:
            speak_output = "Today, you've completed "
            for i, (exercise, quantity) in enumerate(reps):
                speak_output_part = f"{quantity} {exercise}"
                if i == 0 and i == len(reps) - 1:
                    speak_output += speak_output_part + '.'
                elif i < len(reps) - 1:
                    speak_output += speak_output_part + ", "
                else:
                    speak_output += ' and ' + speak_output_part + '.'
        ask_output = "Can I help with anything else?"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(ask_output)
                .response
        )


class HelpIntentHandler(AbstractRequestHandler):
    """Handler for Help Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "You can say track followed by a quantity and exercise " \
                       "name, or ask for your total reps for today."

        return (
            handler_input.response_builder
                .speak(speak_output)
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
        speech = "Hmm, I'm not sure. You can say track followed by a quantity and exercise " \
                 "name, or get your total reps for today. What would you like to do?"
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


sb = CustomSkillBuilder(api_client=DefaultApiClient())

sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(CreateRepsIntentHandler())
sb.add_request_handler(AggregateRepsIntentHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(FallbackIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_request_handler(IntentReflectorHandler())

sb.add_exception_handler(CatchAllExceptionHandler())

lambda_handler = sb.lambda_handler()