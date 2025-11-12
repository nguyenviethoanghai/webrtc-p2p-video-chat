const socket = io("http://localhost:5000");
const localVideo = document.getElementById("localVideo");
const remoteVideo = document.getElementById("remoteVideo");

let localStream, peerConnection;
const config = { iceServers: [{ urls: "stun:stun.l.google.com:19302" }] };

socket.on("offer", async (offer) => {
  peerConnection = createPeerConnection();
  await peerConnection.setRemoteDescription(offer);
  const answer = await peerConnection.createAnswer();
  await peerConnection.setLocalDescription(answer);
  socket.emit("answer", answer);
});

socket.on("answer", (answer) => {
  peerConnection.setRemoteDescription(answer);
});

socket.on("ice-candidate", (candidate) => {
  peerConnection.addIceCandidate(new RTCIceCandidate(candidate));
});

function createPeerConnection() {
  const pc = new RTCPeerConnection(config);
  pc.onicecandidate = (event) => {
    if (event.candidate) socket.emit("ice-candidate", event.candidate);
  };
  pc.ontrack = (event) => {
    remoteVideo.srcObject = event.streams[0];
  };
  localStream.getTracks().forEach((track) => pc.addTrack(track, localStream));
  return pc;
}

document.getElementById("startBtn").onclick = async () => {
  localStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
  localVideo.srcObject = localStream;
  peerConnection = createPeerConnection();
  const offer = await peerConnection.createOffer();
  await peerConnection.setLocalDescription(offer);
  socket.emit("offer", offer);
};

document.getElementById("endBtn").onclick = () => {
  peerConnection.close();
  socket.disconnect();
};
