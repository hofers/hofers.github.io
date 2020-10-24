---
title: Contact
h1: Contact Sean
h2: Drop me a line via this form
place-in-menu: 4
permalink: /contact
tags: css js
---
<div id="main">
  <form id="form" action="#">
    <fieldset id="form-fields">
      <div>
        <label>Name</label>
        <input type="text" name="name" id="name" required>
      </div>
      <div>
        <label>Email</label>
        <input type="email" name="email" id="email" required>
      </div>
      <div>
        <label>Message</label>
        <textarea name="message" id="message" placeholder="What's up?" rows="6" required></textarea>
      </div>
      <div>
        <label>Attachments (optional)</label>
        <input type="file" name="attachments" id="attachments"  multiple>
      </div>
      <div style="padding-top:0.7rem;">
        <input type="submit" value="Submit">
      </div>
      <div id="loader" class="loader hidden"></div>
    </fieldset>
  </form>
  <div id="400e" class="hidden">
    <p class="error">Oops! It looks like there's a problem with your contact request. Make sure you've included your name, email, and message and try again.</p>
  </div>
  <div id="500e" class="hidden">
    <p class="error">Oops! It looks like there was a problem submitting this message. Please try again later, or email me directly at {% my_email %}. </p>
  </div>
  <p>Or email me directly at {% my_email %}. </p>
</div>
<div id="success" class="hidden">
  <p>Thanks for reaching out!</p>
  <p>I'll get back to you as soon as I can. In the meantime, feel free to check out my <a href="/resume">resume</a> or <a href="/portfolio">portfolio</a>. </p>
</div>