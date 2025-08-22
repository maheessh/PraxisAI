import { useState } from "react";
import { FileUpload } from "./components/FileUpload";
import { SlideDeck } from "./components/SlideDeck";
import { QuizSection } from "./components/QuizSection";
import { ExamSection } from "./components/ExamSection";

export default function App() {
  const [currentView, setCurrentView] = useState("home");

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-white">
      {/* Navbar */}
      <nav className="bg-white shadow-md px-6 py-4 flex justify-between items-center">
        <h1 className="text-2xl font-bold text-blue-700">Praxis AI</h1>
        <div className="flex gap-6">
          <button onClick={() => setCurrentView("home")} className="hover:text-blue-600">
            Home
          </button>
          <button onClick={() => setCurrentView("slides")} className="hover:text-blue-600">
            Slides
          </button>
          <button onClick={() => setCurrentView("quiz")} className="hover:text-blue-600">
            Quiz
          </button>
          <button onClick={() => setCurrentView("exam")} className="hover:text-blue-600">
            Exam
          </button>
        </div>
      </nav>

      {/* Main Content */}
      <main className="p-6">
        {currentView === "home" && <FileUpload />}
        {currentView === "slides" && <SlideDeck />}
        {currentView === "quiz" && <QuizSection />}
        {currentView === "exam" && <ExamSection />}
      </main>
    </div>
  );
}
