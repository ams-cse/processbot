$('#live-chat').hide(0);

function submit_userText(userText) {
  $.post("/send_userText", { userText: userText }, handle_response);

  function handle_response(responseObject) {
    
    console.log("ResponseObject:")
    console.log(responseObject);

    if (responseObject.currentProcessStep !== "")
      viewer.get('canvas').addMarker(responseObject.currentProcessStep, 'highlight');

    // Bot Messages ausgeben
    indexGlobal = 0;
    responseObject.messages.forEach(function(message,index) {
      indexGlobal = index;
      setTimeout(function(){
        botui.message.bot({
          delay: 1000,
          loading: true,
          content: message
        });
      },1500*index);
    });
    
    // Buttons? --> anzeigen & geklickter Button auslesen
    if (responseObject.buttons != []) {
      // TODO : Eingabe Feld ausblenden
      setTimeout(function(){
        botui.action
          .button({
            action: responseObject.buttons
          })
          .then(function(pressedButton) {
            // Wird ausgeführt, wenn ein Button geklickt wurde
            submit_button(responseObject.currentProcess, responseObject.currentProcessStep, pressedButton.value);
          });
      },1500*indexGlobal+1000);
    }
  }
}

// ResponseObject mitübergeben, damit klar ist, in welchem Prozessschritt man sich befindet
function submit_button(currentProcess, currentProcessStep, pressedButtonValue) {
  console.log("currentProcess:")
  console.log(currentProcess)
  console.log("currentProcessStep:")
  console.log(currentProcessStep)
  console.log("pressedButtonValue:")
  console.log(pressedButtonValue)

  $.post("/send_button", { pressedButtonValue: pressedButtonValue, currentProcess: currentProcess, currentProcessStep: currentProcessStep }, handle_response);

  function handle_response(responseObject) {
    console.log ("########## im handle Response von submitButton angekommen")
    console.log("ResponseObject:")
    console.log(responseObject);

    if (responseObject.currentProcessStep !== "")
      viewer.get('canvas').addMarker(responseObject.currentProcessStep, 'highlight');

    // Bot Messages ausgeben
    indexGlobal = 0;
    responseObject.messages.forEach(function(message,index) {
      indexGlobal = index;
      setTimeout(function(){
        botui.message.bot({
          delay:1000,
          loading: true,
          content: message
        });
      },1500*index);
    });
  
    // Buttons? --> anzeigen & geklickter Button auslesen
    if (responseObject.buttons != []) {
      // TODO : Eingabe Feld ausblenden
      setTimeout(function(){
        botui.action
          .button({
            action: responseObject.buttons
          })
          .then(function(pressedButton) {
            // Wird ausgeführt, wenn ein Button geklickt wurde
            submit_button(responseObject.currentProcess, responseObject.currentProcessStep, pressedButton.value);
          });
      },1500*indexGlobal+1000);
    }

  }

}


// Leitet die Usereingaben ans Backend weiter
var userText;
$(document).ready(function() {
  $("#InputField").keypress(function(e) {
    if (e.keyCode == 13) {
      userText = $("#InputField").val();
      submit_userText(userText);
      console.log($("#InputField").val());
      $("#InputField").val("");

      // Zeigt den UserText im Chatfenster an
      botui.message.human({
        content: userText
      });
    }
  });
});



	$('.chat-close').on('click', function(e) {

		e.preventDefault();
    $('#live-chat').fadeOut(300);
    $('#prime').fadeIn(300);

	});


$('#prime').on('click', function(e) {
  e.preventDefault();
  $('#live-chat').fadeIn(300);
  $('#prime').hide(0);

});
