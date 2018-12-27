"""
Analyze twitter followees
"""

import os
import logging
import pprint
from flask import Flask, request, redirect, session
import tweepy
from dotenv import load_dotenv

APP = Flask(__name__)
APP.config["CONSUMER_TOKEN"] = os.environ.get("CONSUMER_TOKEN")
APP.config["CONSUMER_SECRET"] = os.environ.get("CONSUMER_SECRET")
APP.secret_key = os.environ.get(
    "CONSUMER_SECRET"
)  # using the twitter secret for session storage
APP.config["CONSUMER_CALLBACK"] = os.environ.get("CONSUMER_CALLBACK", "")

LOGFORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
logging.basicConfig(level=logging.DEBUG, format=LOGFORMAT)


@APP.route("/")
def default():
    """
    main app
    """
    auth = tweepy.OAuthHandler(
        APP.config["CONSUMER_TOKEN"],
        APP.config["CONSUMER_SECRET"],
        APP.config["CONSUMER_CALLBACK"],
    )

    if "access_token" not in session or "access_token_secret" not in session:
        # not logged in
        redirect_url = auth.get_authorization_url()
        session["request_token"] = auth.request_token["oauth_token"]
        return redirect(redirect_url)

    # user already logged in / authorized
    auth.set_access_token(
        session["access_token"], session["access_token_secret"]
    )
    api = tweepy.API(
        auth,
        wait_on_rate_limit=True,
        wait_on_rate_limit_notify=True,
        cache=tweepy.cache.FileCache(".cache", timeout=24 * 60 * 60),
    )

    users_following_me = [
        follower for follower in tweepy.Cursor(api.followers_ids).items()
    ]

    # logging.debug((len(users_following_me), users_following_me))

    prettyprint = pprint.PrettyPrinter(indent=4)
    details = []
    for followee in tweepy.Cursor(api.friends).items(1000):
        infos = {
            key: getattr(followee, key)
            for key in [
                "created_at",
                "favourites_count",
                "followers_count",
                "friends_count",
                "lang",
                "listed_count",
                "location",
                "name",
                "screen_name",
                "statuses_count",
                "default_profile",
                "default_profile_image",
                "following",
            ]
        }
        try:
            infos["last_status_update"] = followee.status.created_at
        except AttributeError:
            infos["last_status_update"] = None
        infos["follows_me"] = followee.id in users_following_me
        # infos['display_urls'] = followee.entities.get('url', {})
        infos["expanded_urls"] = [
            x["expanded_url"]
            for u in followee.entities.get("url", {})
            for x in followee.entities["url"]["urls"]
            if u == "urls"
        ]
        infos["link"] = "https://twitter.com/" + infos["screen_name"]
        if infos["follows_me"]:
            continue
        if infos["lang"] in ["en", "de", "en-gb", "fi"]:
            continue
        details.append(infos)
    return prettyprint.pformat(details)


@APP.route("/callback")
def callback():
    """
    twitter auth callback
    """
    verifier = request.args.get("oauth_verifier", None)
    auth = tweepy.OAuthHandler(
        APP.config["CONSUMER_TOKEN"],
        APP.config["CONSUMER_SECRET"],
        APP.config["CONSUMER_CALLBACK"],
    )
    token = session.get("request_token", None)
    del session["request_token"]
    auth.request_token = {"oauth_token": token, "oauth_token_secret": verifier}

    # try:
    auth.get_access_token(verifier)
    # except tweepy.TweepError:
    #    return 'Error! Failed to get access token: {0}'.format(str(auth))
    session["access_token"] = auth.access_token
    session["access_token_secret"] = auth.access_token_secret
    return redirect("/")


if __name__ == "__main__":
    load_dotenv()
    APP.run(host="0.0.0.0", port=os.environ.get("listenport", 8080))
