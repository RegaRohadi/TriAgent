import { useEffect, useState } from "react";
import { RiSendPlaneLine } from "@remixicon/react";
import { Button } from "@/components/base/buttons/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/base/card/card";
import { Input } from "@/components/base/input/input";
import { TextArea } from "@/components/base/input/textarea";
import { Select, SelectItem } from "@/components/base/select/select";

export function ProcessForm({ samples, onRun, running }) {
  const [sampleName, setSampleName] = useState("");
  const [sender, setSender] = useState("");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");

  useEffect(() => {
    if (!samples.length) return;
    const params = new URLSearchParams(location.search);
    const wanted = params.get("sample");
    if (!wanted) return;
    const match = samples.find((s) => s.name === wanted || s.name.startsWith(wanted));
    if (!match) return;
    applySample(match);
    if (params.get("run")) onRun({ subject: match.subject, body: match.body, sender: match.sender });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [samples]);

  function applySample(s) {
    setSampleName(s.name);
    setSubject(s.subject);
    setBody(s.body);
    setSender(s.sender);
  }

  function handleSampleChange(name) {
    setSampleName(name);
    const s = samples.find((x) => x.name === name);
    if (s) applySample(s);
  }

  function handleSubmit() {
    const trimmedBody = body.trim();
    if (!trimmedBody) return;
    onRun({ subject: subject.trim() || null, body: trimmedBody, sender: sender.trim() || null });
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Incoming email</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="flex flex-col gap-1">
          <span id="sample-label" className="text-body-medium text-text-primary">
            Load a sample
          </span>
          <Select
            aria-labelledby="sample-label"
            placeholder="— choose a sample email —"
            value={sampleName || null}
            onChange={handleSampleChange}
            className="w-full"
            popoverClassName="w-(--trigger-width)"
          >
            {samples.map((s) => (
              <SelectItem key={s.name} id={s.name} textValue={`${s.name} — ${s.subject}`}>
                <span className="truncate">
                  {s.name} — {s.subject}
                </span>
              </SelectItem>
            ))}
          </Select>
        </div>

        <Input
          label="Sender address (used for the contact-frequency rule)"
          placeholder="customer@example.com"
          value={sender}
          onChange={setSender}
        />

        <Input label="Subject" placeholder="Question about my invoice" value={subject} onChange={setSubject} />

        <TextArea
          label="Body"
          rows={7}
          placeholder="Type or paste the email body here"
          value={body}
          onChange={setBody}
        />

        <Button
          onClick={handleSubmit}
          disabled={running || !body.trim()}
          leadingIcon={RiSendPlaneLine}
          className="self-start"
        >
          Process email
        </Button>
      </CardContent>
    </Card>
  );
}
