
import { useState } from "react";
import { Button, FileInput, Text, List } from "@mantine/core";
import { processContent } from "../services/api";

export default function FileUpload({ onContentReady }) {
  const [file, setFile] = useState(null);
  const [topics, setTopics] = useState([]);

  const handleUpload = async () => {
    if (!file) return;
    const res = await processContent(file);
    setTopics(res.slide_topics);
    onContentReady(res.full_content); // pass extracted text upward
  };

  return (
    <div>
      <FileInput
        placeholder="Upload PDF or TXT"
        value={file}
        onChange={setFile}
      />
      <Button mt="md" onClick={handleUpload}>
        Process Content
      </Button>

      {topics.length > 0 && (
        <div>
          <Text fw={700} mt="md">Suggested Slide Topics:</Text>
          <List spacing="xs" size="sm" withPadding>
            {topics.map((t, i) => (
              <List.Item key={i}>{t}</List.Item>
            ))}
          </List>
        </div>
      )}
    </div>
  );
}
