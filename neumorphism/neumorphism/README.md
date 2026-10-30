# Neumorphism Login Form

Extract the whole `neumorphism/` folder, then open `index.html` in a browser.
Everything required is included. No installation, build step, CDN, or internet connection is needed.

## Included files

- `index.html`: sign in
- `sign-up.html`: account creation demo
- `reset-password.html`: reset request demo
- `new-password.html`: new-password demo
- `style.css`: this design's styling
- `script.js`: this design's behavior
- `form-utils.js`: shared validation, accessibility, and login lifecycle
- `README.md`: these instructions

Keep these files together when moving or hosting the form. You can also serve this
folder with `python3 -m http.server 8000` and visit http://localhost:8000/.

## Demo and integration

Sign-in, reset, signup, and provider actions are demonstrations. Any valid email and
nonempty password succeeds except `admin@demo.com` with `wrongpassword`, which shows
an error. Never enter real credentials into a demo. The other screens create no
accounts, send no email, change no passwords, and save nothing. New passwords
require at least 15 characters; spaces and paste are supported. Use `error@demo.com`
on sign-up/reset requests or `demo-error-password` on the new-password screen to
preview a temporary service error, then edit the value and retry.

To connect your backend, pass an asynchronous `authenticate(email, password, data)`
callback in the `super({ ... })` options in `script.js`. Resolve on successful
sign-in and reject with a safe user-facing Error on failure. Passwords are passed
unchanged. The server owns credential verification, session security, and rate limits.

For the companion screens, supply separate asynchronous `createAccount(email, password, data)`,
`requestReset(email, password, data)`, and `resetPassword(email, password, data)` options.
The reset adapter must obtain a token from your real reset flow and verify it on the
server before changing any password. Use generic reset responses, expiring single-use
tokens, server-side validation, rate limits, and secure session handling. Client-side
checks are usability helpers. Replace demo notices, labels, and success copy when
integrating your service. These demo screens are not production authentication.

Customize colors in `style.css` and labels in `index.html`.

Created by Aigars Silkalns for Colorlib.
Source and documentation: https://github.com/puikinsh/login-forms/tree/main/forms/neumorphism
Collection: https://puikinsh.github.io/login-forms/
