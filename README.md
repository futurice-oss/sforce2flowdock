[![Build Status](https://travis-ci.org/futurice/sforce2flowdock.svg?branch=master)](https://travis-ci.org/futurice/sforce2flowdock)

# Post SalesForce Opportunities and Opportunities Chatter to Flowdock

This file describes how to set up and run in dev.
The DEPLOY file describes a suggested deployment setup.

## Setup:

• Python3 virtual environment (e.g. `virtualenv -p python3 env`)
`pip install -r req.txt`

• `config/` → Your configuration, including OAuth2 tokens
```bash
cp sforce-config.json.template sforce-config.json
```

[This page](http://www.salesforce.com/us/developer/docs/api_rest/Content/intro_understanding_web_server_oauth_flow.htm)
explains how to find the fields (`client_id`, `client_secret`, etc.).

Run `./sforce-show-api-versions.py` to see the options for the `apiVersionUrl`.

• current directory
Always have your current directory set to the one containing this README file.

## Test:

```bash
./test.sh
```

• Explore the SalesForce API by hand
```bash
./sforce-get.py --help
```
