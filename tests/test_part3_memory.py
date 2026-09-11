from __future__ import annotations

from part3_doc_agent.memory import ConversationMemory, normalise_session_id
from part3_doc_agent.models import MemoryFact

def make(tmp_path, **kwargs) -> ConversationMemory:
    return ConversationMemory("test", session_dir=tmp_path, **kwargs)

def test_facts_are_remembered(tmp_path):
    memory = make(tmp_path)
    changed = memory.remember([MemoryFact(key="name", value="Rega"), MemoryFact(key="plan", value="Business")])

    assert changed == ["name", "plan"]
    assert memory.recall("name") == "Rega"

def test_key_spellings_are_folded_together(tmp_path):
    memory = make(tmp_path)
    memory.remember([MemoryFact(key="User Name", value="Rega")])

    assert memory.profile == {"name": "Rega"}

def test_restating_a_known_fact_is_not_a_change(tmp_path):
    memory = make(tmp_path)
    memory.remember([MemoryFact(key="name", value="Rega")])

    assert memory.remember([MemoryFact(key="name", value="Rega")]) == []

def test_a_correction_overwrites_the_earlier_value(tmp_path):
    memory = make(tmp_path)
    memory.remember([MemoryFact(key="name", value="Rega")])
    memory.remember([MemoryFact(key="name", value="Reggie")])

    assert memory.recall("name") == "Reggie"

def test_empty_values_are_ignored(tmp_path):
    memory = make(tmp_path)

    assert memory.remember([MemoryFact(key="name", value="   ")]) == []
    assert memory.profile == {}

def test_profile_is_capped(tmp_path):
    memory = make(tmp_path, max_facts=2)
    memory.remember([MemoryFact(key=f"k{i}", value=str(i)) for i in range(5)])

    assert len(memory.profile) == 2

def test_buffer_keeps_only_the_recent_window(tmp_path):
    memory = make(tmp_path, window_turns=2)
    for i in range(5):
        memory.add_turn("user", f"q{i}")
        memory.add_turn("agent", f"a{i}")

    assert len(memory.turns) == 4
    assert memory.turns[0].content == "q3"

def test_name_survives_after_the_buffer_has_scrolled_past_it(tmp_path):
    memory = make(tmp_path, window_turns=2)
    memory.remember([MemoryFact(key="name", value="Rega")])
    memory.add_turn("user", "Hi, I'm Rega.")
    memory.add_turn("agent", "Hello Rega.")

    for i in range(6):
        memory.add_turn("user", f"unrelated question {i}")
        memory.add_turn("agent", f"unrelated answer {i}")

    assert "Rega" not in "\n".join(t.content for t in memory.turns), "introduction should have scrolled away"
    assert memory.recall("name") == "Rega"
    assert "name: Rega" in memory.as_prompt_context()

def test_empty_memory_says_so_explicitly(tmp_path):
    context = make(tmp_path).as_prompt_context()

    assert "not been told anything" in context

def test_memory_survives_a_restart(tmp_path):
    memory = make(tmp_path)
    memory.remember([MemoryFact(key="name", value="Rega")])
    memory.add_turn("user", "hello")
    memory.save()

    reloaded = ConversationMemory.load("test", session_dir=tmp_path)

    assert reloaded.recall("name") == "Rega"
    assert len(reloaded.turns) == 1

def test_a_corrupt_session_file_starts_an_empty_conversation(tmp_path):
    (tmp_path / "broken.json").write_text("{not json", encoding="utf-8")

    memory = ConversationMemory.load("broken", session_dir=tmp_path)

    assert memory.profile == {}
    assert memory.turns == []

def test_session_ids_cannot_escape_the_session_directory():
    assert normalise_session_id("../../.env") == "env"
    assert normalise_session_id("a/b\\c") == "a-b-c"
    assert normalise_session_id("") == "default"

def test_session_file_stays_inside_the_session_directory(tmp_path):
    memory = ConversationMemory("../../escape", session_dir=tmp_path)

    assert memory.path.parent == tmp_path
