import web, app, hashlib, uuid
import urllib2, recaptchaCli, conf

class LogIn:
	def GET(self):
		webinput = web.input()
		
		return self.Render()

	def POST(self):
		users = web.ctx.users
		webinput = web.input()

		username = webinput["username"]
		password = webinput["password"]

		#Check if username already exists
		result = users.select("users", where="username=$u", vars={"u":username})
		result = list(result)
		numFound = len(result)
		if numFound == 0:
			return self.Render("Username not found")

		#Check password
		record = result[0]
		password_hash = hashlib.sha512(password + record.salt).hexdigest()
		if record.password_hash != password_hash:
			return self.Render("Incorrect password. Please try again.")

		web.ctx.session.username = username
		return self.Render()

	def Render(self, actionMessage = None):
		webinput = web.input()
		

		return app.RenderTemplate("login.html", webinput=webinput, session=web.ctx.session, actionMessage=actionMessage)

class LogOut:
	def GET(self):
		db = web.ctx.db
		webinput = web.input()
		
		web.ctx.session.username = None
		return app.RenderTemplate("logout.html", webinput=webinput, session=web.ctx.session)

class Register:
	def GET(self):
		db = web.ctx.db
		webinput = web.input()
		
		return self.Render()

	def POST(self):
		db = web.ctx.db
		users = web.ctx.users
		webinput = web.input()
		env = web.ctx.env

		#Check recaptcha
		if conf.recaptchaEnabled:
			userIp = env["REMOTE_ADDR"]		
			ok, recapErrors = recaptchaCli.Check(conf.recaptchaSecret, webinput["g-recaptcha-response"], userIp)

			if not ok:
				errorStr = ",".join(recapErrors)
				return self.Render("Recaptcha problem. Please try again. {0}".format(errorStr))

		password = webinput["password"]

		#Check passwords match
		if password != webinput["password2"]:
			return self.Render("Passwords do not match")

		#Check password
		if password in ["password"]:
			return self.Render("Invalid password")
		if len(password) < 5:
			return self.Render("Password too short")

		username = webinput["username"]
		email = webinput["email"]

		if len(email) > 0:
			ampPos = email.find("@")
			if ampPos == -1:
				return self.Render("Invalid email")

		if len(password) < 3:
			return self.Render("Username too short")
		if len(password) > 100:
			return self.Render("Username too long")

		#Check if username already exists
		result = users.select("users", where="username=$u", vars={"u":username})
		numFound = len(list(result))
		if numFound != 0:
			return self.Render("Username already in use")

		#Add user
		salt = uuid.uuid4().hex
		password_hash = hashlib.sha512(password + salt).hexdigest()
		users.insert("users", username=username, salt=salt, password_hash=password_hash, email=email)

		web.ctx.session.username = username

		return self.Render(actionTxt = "All good", justRegistered = True)

	def Render(self, actionTxt = None, justRegistered = False):
		db = web.ctx.db
		webinput = web.input()

		return app.RenderTemplate("register.html", webinput=webinput, 
			actionTxt=actionTxt, 
			recaptchaEnabled = conf.recaptchaEnabled,
			justRegistered = justRegistered,
			session = web.ctx.session)

