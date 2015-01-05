import urllib2, json

def Check(recaptchaSecret, response, userIp):
	verifyUrl = "https://www.google.com/recaptcha/api/siteverify"
	
	url = "{0}?secret={1}&response={2}&remoteip={3}".format(
		verifyUrl,
		recaptchaSecret,
		response,
		userIp)

	ha = urllib2.urlopen(url)
	resp = ha.read()
		
	respDec = json.loads(resp)
	ok = respDec["success"]
	errors = []
	if "error-codes" in respDec:
		errors = respDec["error-codes"]

	return ok, errors

