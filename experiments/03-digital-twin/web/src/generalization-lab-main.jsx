import * as React from "react";
import { createRoot } from "react-dom/client";

import { GeneralizationLab } from "./components/generalization-lab/GeneralizationLab.jsx";
import "./index.css";
import "./arm-lab.css";
import "./generalization-lab.css";

createRoot(document.getElementById("generalization-lab-root")).render(
  <React.StrictMode>
    <GeneralizationLab />
  </React.StrictMode>,
);
