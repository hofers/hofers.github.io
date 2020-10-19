---
title: Contact
h1: Contact Sean
h2: Drop me a line via this form
place-in-menu: 4
permalink: /contact
tags: css
---
<form action="https://mailthis.to/seanhofer.com%20Contact%20Form" method="POST" encType="multipart/form-data">
    <div>
      <label>Name</label>
      <input type="text" name="name" required>
    </div>
    <div>
      <label>Email</label>
      <input type="email" name="_replyto" required>
    </div>
    <div>
      <label>Message</label>
      <textarea name="message" placeholder="What's up?" rows="6" required></textarea>
    </div>
    <div>
      <label>Attachments (optional)</label>
      <input type="file" name="file">
    </div>
    <div style="padding-top:0.7rem;">
      <input type="hidden" name="_subject" value="Contact via seanhofer.com">
      <input type="hidden" name="_honeypot" value="">
      <input type="hidden" name="_confirmation" value="Thanks for reaching out. I'll get back to you as soon&nbsp;as&nbsp;I&nbsp;can.">
      <input type="submit" value="Submit">
    </div>
</form>
Or email me directly at {% my_email %}. &nbsp;