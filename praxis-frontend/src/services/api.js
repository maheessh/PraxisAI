import axios from "axios";

const API_URL = "http://127.0.0.1:8000"; // your FastAPI backend

export const processContent = async (file) => {
  const formData = new FormData();
  formData.append("file", file);
  const res = await axios.post(`${API_URL}/process-content/`, formData);
  return res.data;
};

export const generateSlides = async (content) => {
  const formData = new FormData();
  formData.append("content", content);
  const res = await axios.post(`${API_URL}/generate-detailed-slides/`, formData);
  return res.data;
};

export const downloadSlidesPDF = async (slidesJson) => {
  const formData = new FormData();
  formData.append("slides_json", JSON.stringify(slidesJson));
  const res = await axios.post(`${API_URL}/download-slides-pdf/`, formData, {
    responseType: "blob",
  });
  return res.data;
};

export const generateQuiz = async (content) => {
  const formData = new FormData();
  formData.append("content", content);
  const res = await axios.post(`${API_URL}/generate-quiz/`, formData);
  return res.data;
};

export const generateExam = async (content) => {
  const formData = new FormData();
  formData.append("content", content);
  const res = await axios.post(`${API_URL}/generate-exam/`, formData);
  return res.data;
};

export const generateAnnouncement = async (content) => {
  const formData = new FormData();
  formData.append("content", content);
  const res = await axios.post(`${API_URL}/generate-announcement/`, formData);
  return res.data;
};
