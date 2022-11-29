import bpy
import base64
import time
import requests

from .. import (
    config,
    operators,
    utils,
)

API_URL = "https://stablehorde.net/api/v2/generate/sync"
SAMPLER_MAP = {
    "DDIM": "k_ddim",
    "PLMS": ""
}

# CORE FUNCTIONS:

def send_to_api(params, img_file, filename_prefix):

    # map the generic params to the specific ones for the Stable Horde API
    stablehorde_params = {
        "prompt": params["prompt"],
        # add a base 64 encoded image to the params
        "source_image": base64.b64encode(img_file.read()).decode(),
        "params": {
            "cfg_scale": params["cfg_scale"],
            "width": params["width"],
            "height": params["height"],
            "denoising_strength": round(1 - params["image_similarity"], 2),
            "seed": str(params["seed"]),
            "steps": params["steps"],
            "sampler_name": params["sampler"],
        }
    }

    # close the image file
    img_file.close()

    # if no api-key specified, use the default non-authenticated api-key
    apikey = utils.get_stable_horde_api_key() if not utils.get_stable_horde_api_key().strip() == "" else "0000000000"

    # create the headers
    headers = {
        "User-Agent": "Blender/" + bpy.app.version_string,
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "apikey": apikey
    }

    # send the API request
    start_time = time.monotonic()
    print("Sending to Stable Horde")
    try:
        response = requests.post(API_URL, json=stablehorde_params, headers=headers, timeout=request_timeout())
        img_file.close()
    except requests.exceptions.ReadTimeout:
        img_file.close()
        return operators.handle_error(f"The server timed out. Try again in a moment, or get help. [Get help with timeouts]({config.HELP_WITH_TIMEOUTS_URL})")
    print("The horde took " + str(time.monotonic() - start_time) + " seconds to imagine this frame.")

    # For debugging
    # print("Send to Stable Horde: " + str(stablehorde_params))
    # print("Received from Stable Horde: " + str(response.json()))

    # handle the response
    if response.status_code == 200:
        return handle_api_success(response, filename_prefix)
    else:
        return handle_api_error(response)


def handle_api_success(response, filename_prefix):

    # ensure we have the type of response we are expecting
    try:
        response_obj = response.json()
        base64_img = response_obj["generations"][0]["img"]
        print(f"Worker: {response_obj['generations'][0]['worker_name']}, " +
              f"queue position: {response_obj['queue_position']}, wait time: {response_obj['wait_time']}, " +
              f"kudos: {response_obj['kudos']}")
    except:
        print("Stable Horde response content: ")
        print(response.content)
        return operators.handle_error("Received an unexpected response from the Stable Horde server.")

    # create a temp file
    try:
        output_file = utils.create_temp_file(filename_prefix + "-", suffix=f".{get_image_format().lower()}")
    except:
        return operators.handle_error("Couldn't create a temp file to save image.")

    # decode base64 image
    try:
        img_binary = base64.b64decode(base64_img.replace("data:image/png;base64,", ""))
    except:
        return operators.handle_error("Couldn't decode base64 image from the Stable Horde server.")

    # save the image to the temp file
    try:
        with open(output_file, 'wb') as file:
            file.write(img_binary)
    except:
        return operators.handle_error("Couldn't write to temp file.")

    # return the temp file
    return output_file


def handle_api_error(response):
    return operators.handle_error("The Stable Horde server returned an error: " + str(response.content))

def get_samplers():
    # NOTE: Keep the number values (fourth item in the tuples) in sync with DreamStudio's
    # values (in stability_api.py). These act like an internal unique ID for Blender
    # to use when switching between the lists.
    return [
        ('k_euler', 'Euler', '', 10),
        ('k_euler_a', 'Euler a', '', 20),
        ('k_heun', 'Heun', '', 30),
        ('k_dpm_2', 'DPM2', '', 40),
        ('k_dpm_2_a', 'DPM2 a', '', 50),
        ('k_lms', 'LMS', '', 60),
        ('k_dpm_fast', 'DPM fast', '', 70),
        ('k_dpm_adaptive', 'DPM adaptive', '', 80),
        ('k_dpmpp_2s_a', 'DPM++ 2S a', '', 110),
        ('k_dpmpp_2m', 'DPM++ 2M', '', 120),
        # TODO: Stable horde does have karras support, but it's a separate boolean
    ]


def default_sampler():
    return 'k_euler_a'


def request_timeout():
    return 600


def get_image_format():
    return 'WEBP'


def max_image_size():
    return 1024 * 1024