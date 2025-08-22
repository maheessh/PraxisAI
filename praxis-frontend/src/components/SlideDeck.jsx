import { useState } from "react";
import { Button, Card, Image, Text, Loader } from "@mantine/core";
import { generateSlides, downloadSlidesPDF } from "../services/api";

export default function SlideDeck({ content }) {
  const [slides, setSlides] = useState([]);
  const [loading, setLoading] = useState(false);

  const handleGenerate = async () => {
    setLoading(true);
    const res = await generateSlides(content);
    setSlides(res.slides);
    setLoading(false);
  };

  const handleDownload = async () => {
    const pdfBlob = await downloadSlidesPDF({ slides });
    const url = window.URL.createObjectURL(new Blob([pdfBlob]));
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", "slides.pdf");
    document.body.appendChild(link);
    link.click();
  };

  return (
    <div>
      <Button onClick={handleGenerate} loading={loading}>
        Generate Slide Deck
      </Button>

      {slides.length > 0 && (
        <div>
          <Text fw={700} mt="md">Generated Slides:</Text>
          {slides.map((slide, i) => (
            <Card key={i} shadow="sm" mt="md" padding="lg">
              <Text fw={600}>{slide.title}</Text>
              <Text size="sm">{slide.subtitle}</Text>
              <ul>
                {slide.bullet_points.map((bp, j) => (
                  <li key={j}>{bp}</li>
                ))}
              </ul>
              {slide.image_base64 && (
                <Image
                  src={`data:image/png;base64,${slide.image_base64}`}
                  alt="Slide Preview"
                  mt="sm"
                />
              )}
            </Card>
          ))}

          <Button mt="lg" color="green" onClick={handleDownload}>
            Download PDF
          </Button>
        </div>
      )}
    </div>
  );
}
