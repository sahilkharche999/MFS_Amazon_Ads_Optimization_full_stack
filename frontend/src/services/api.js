import axios from "axios";

const api = axios.create({
  baseURL: "http://18.220.190.68:8000/api",
});

export default api;
