import { useState } from "react";
import { Button, Card, Text } from "@mantine/core";
import { generateQuiz } from "../services/api";

export default function Quiz({ content }) {
  const [quiz, setQuiz] = useState(null);

  const handleGenerate = async () => {
    const res = await generateQuiz(content);
    setQuiz(res.quiz);
  };

  return (
    <div>
      <Button onClick={handleGenerate}>Generate Quiz</Button>
      {quiz && quiz.map((q, i) => (
        <Card key={i} mt="md">
          <Text fw={600}>{q.question}</Text>
          <ul>
            {q.options.map((opt, j) => <li key={j}>{opt}</li>)}
          </ul>
          <Text size="sm" c="dimmed">Answer: {q.answer}</Text>
          <Text size="xs">{q.explanation}</Text>
        </Card>
      ))}
    </div>
  );
}
