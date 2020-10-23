document.addEventListener("DOMContentLoaded", function() {
  document.getElementById("form").addEventListener("submit", function(e) {
    e.preventDefault()
    sendRequest()
  })
})

async function sendRequest() {
  let xhr = new XMLHttpRequest()
  let searchParams = new URLSearchParams()
  let attachments = []
  let names = []

  for (file of document.getElementById("attachments").files) {
    let attachment = await readFileAsync(file)
    attachments.push(attachment)
    names.push(file.name)
  }

  searchParams.append("name", document.getElementById("name").value)
  searchParams.append("email", document.getElementById("email").value)
  searchParams.append("message", document.getElementById("message").value)

  if (attachments.length > 0) {
    searchParams.append("attachment_names", [names])
    searchParams.append("attachments", [attachments])
  }

  xhr.open("POST", "https://us-central1-coherent-coder-193013.cloudfunctions.net/contact-form ", true)
  xhr.setRequestHeader("Content-Type", "application/x-www-form-urlencoded")

  xhr.onload = function() {
    finishLoading()
    if (xhr.status == 200) {
      succeed()
    } else {
      fail()
    }
  }

  xhr.send(searchParams.toString())
  startLoading()
}

function startLoading() {
  document.getElementById("form-fields").disabled = true
  document.getElementById("loader").classList.remove("hidden")
}

function finishLoading() {
  document.getElementById("form-fields").disabled = false
  document.getElementById("loader").classList.add("hidden")
}

function succeed() {
  document.getElementById("main").classList.add("hidden")
  document.getElementById("failure").classList.add("hidden")
  document.getElementById("success").classList.remove("hidden")
}

function fail() {
  document.getElementById("failure").classList.remove("hidden")
}

function readFileAsync(file) {
  return new Promise((resolve, reject) => {
    let reader = new FileReader()

    reader.onload = () => {
      var b64 = reader.result.replace(/^data:.+;base64,/, '')
      resolve(b64)
    };

    reader.onerror = reject

    reader.readAsDataURL(file)
  })
}