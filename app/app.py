import asyncio
import logging
import os
import secrets
import signal
import sys
from datetime import datetime
from typing import Any
from flask import Flask, render_template
from flask_assets import Environment, Bundle
from flask_caching import Cache

logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.DEBUG)

app = Flask(__name__)
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
app.secret_key = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex())

if os.environ.get("FLASK_DEBUG", "False") == "True":
	cache_config={
		'CACHE_TYPE': 'null'
	}
else:
	# 600 seconds = 10 minutes
	cache_config={
		'CACHE_TYPE': 'simple',            
		'CACHE_DEFAULT_TIMEOUT': 600
	}
	from flask_minify import Minify
	Minify(app=app, html=True, js=True, cssless=True)
	
cache = Cache(app, config=cache_config)
page_timeout = int(os.environ.get('CACHE_PAGE_TIMEOUT', 600))

assets = Environment(app)

css = Bundle(
		'css/*.css',
		filters="cssmin",
		output="assets/common.css"
)
assets.register('css_all', css)
css.build()

@app.context_processor
def inject_current_date():
	return {
		'today_date': datetime.now(),
		'site_title':	os.environ.get('SITE_TITLE', 'Prototype')
	}


@app.route('/')
def index(tab_name=None):
	return render_template('index.html')


###############################################################################
#
# Main Startup Code
#
###############################################################################

if __name__ == '__main__':	
	port = int(os.environ.get("FLASK_PORT", os.environ.get("ONBOARD_PORT", 9830)))
	development = bool(os.environ.get("FLASK_ENV", "development")  == "development")
	if development:
		app.run(port=port, debug=bool(os.environ.get("FLASK_DEBUG", "True")))
		if bool(os.environ.get('WERKZEUG_RUN_MAIN')):
			print("")
			app.logger.info("Shutting down...")
		sys.exit()
	else:
		try:
			from hypercorn.config import Config
			from hypercorn.asyncio import serve

			shutdown_event = asyncio.Event()

			def _signal_handler(*_: Any) -> None:
				app.logger.info("Shutting down...")
				shutdown_event.set()

			config = Config()
			config.accesslog="-"
			config.errorlog="-"
			config.loglevel="DEBUG"
			config.bind = f"0.0.0.0:{port}"
			loop = asyncio.new_event_loop()
			loop.add_signal_handler(signal.SIGTERM, _signal_handler)
			loop.run_until_complete(
					serve(app, config, shutdown_trigger=shutdown_event.wait)
			)
		except KeyboardInterrupt:
			app.logger.info("Shutting down...")
			sys.exit()
	