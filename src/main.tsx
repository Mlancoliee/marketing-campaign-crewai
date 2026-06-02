import React from "react"
import ReactDOM from "react-dom/client"
import App from "./App"
import { initLocale } from "./i18n"
import "./styles/index.css"

initLocale()

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
