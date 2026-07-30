(() => {
  "use strict";

  window.NoorState = {
    health: null,
    detections: [],
    zones: [],
    events: [],

    frameSize: {
      width: 1280,
      height: 720
    },

    drawing: false,
    startX: 0,
    startY: 0,
    temp: null
  };
})();
