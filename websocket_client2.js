document.addEventListener('DOMContentLoaded', function(){
    const websocketClient = new WebSocket("ws://localhost:12345");

    const messageContainer = document.querySelector("#message_container");
    const messageInput = document.querySelector("[name=message_input]");
    const sendMessageButton = document.querySelector("[name=send_message_button]");

    console.log(messageInput);
    console.log(sendMessageButton);
    console.log(messageContainer);


    websocketClient.onopen = function(){
        websocketClient.send("client2")
        
        sendMessageButton.onclick = function(){
            websocketClient.send(messageInput.value);
        }

        websocketClient.onmessage = function(message){
            const newMassage = document.createElement("div");
            newMassage.innerHTML = message.data;
            messageContainer.appendChild(newMassage);
        }
    };


}, false);