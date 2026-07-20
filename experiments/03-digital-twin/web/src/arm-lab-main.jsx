import * as React from "react";
import { createRoot } from "react-dom/client";

import { ArmLab } from "./components/arm-lab/ArmLab.jsx";
import "./index.css";
import "./arm-lab.css";

createRoot(document.getElementById("arm-lab-root")).render(
  <React.StrictMode>
    <ArmLab />
  </React.StrictMode>,
);
