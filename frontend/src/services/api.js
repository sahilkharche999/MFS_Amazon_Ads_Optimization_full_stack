import axios from "axios";

const api = axios.create({
  baseURL: "mfs-backend:8000/api",
});

export default api;
