import axios from "axios";

const api = axios.create({
  baseURL: "http://mfs-backend:8000/api", // FastAPI backend
});

export default api;
