import { BrowserRouter, Routes, Route } from "react-router-dom";
import UploadPage from "./pages/UploadPage";
import JobPage from "./pages/JobPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<UploadPage />} />
        <Route path="/jobs/:jobId" element={<JobPage />} />
      </Routes>
    </BrowserRouter>
  );
}
