import { useEffect, useState, type FormEvent } from "react";
import {
  Check,
  ChevronDown,
  ChevronUp,
  GripVertical,
  LoaderCircle,
  Pencil,
  Plus,
  Quote,
  Trash2,
  X,
} from "lucide-react";

import { deckBridge } from "@/bridge";
import { DeckPanel } from "@/components/deck/DeckPanel";
import { Button } from "@/components/ui/button";
import { CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { CatchPhrase } from "../../../shared/types";

function moveItem(
  phrases: CatchPhrase[],
  sourceId: string,
  targetId: string,
): CatchPhrase[] {
  const sourceIndex = phrases.findIndex((phrase) => phrase.id === sourceId);
  const targetIndex = phrases.findIndex((phrase) => phrase.id === targetId);
  if (sourceIndex < 0 || targetIndex < 0 || sourceIndex === targetIndex) {
    return phrases;
  }
  const next = [...phrases];
  const [moved] = next.splice(sourceIndex, 1);
  next.splice(targetIndex, 0, moved);
  return next;
}

function newPhraseId(): string {
  return `phrase-${crypto.randomUUID()}`;
}

const inputClassName =
  "h-8 min-w-0 border border-[#52525b] bg-[#111113] px-2 text-xs text-[#f4f4f5] outline-none placeholder:text-[#71717a] focus:border-primary focus:ring-1 focus:ring-primary/30";

export function CatchPhrasesPanel() {
  const [phrases, setPhrases] = useState<CatchPhrase[]>([]);
  const [draft, setDraft] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingText, setEditingText] = useState("");
  const [draggedId, setDraggedId] = useState<string | null>(null);
  const [dragTargetId, setDragTargetId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void deckBridge
      .getCatchPhrases()
      .then((next) => {
        if (active) setPhrases(next);
      })
      .catch((reason: unknown) => {
        if (active) {
          setError(
            reason instanceof Error
              ? reason.message
              : "Could not load the catch phrases.",
          );
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const persist = async (next: CatchPhrase[]): Promise<boolean> => {
    if (saving || next === phrases) return false;
    const previous = phrases;
    setPhrases(next);
    setSaving(true);
    setError(null);
    try {
      setPhrases(await deckBridge.setCatchPhrases(next));
      return true;
    } catch (reason) {
      setPhrases(previous);
      setError(
        reason instanceof Error
          ? reason.message
          : "Could not save the catch phrases.",
      );
      return false;
    } finally {
      setSaving(false);
    }
  };

  const addPhrase = async (event: FormEvent) => {
    event.preventDefault();
    const text = draft.trim();
    if (!text || saving) return;
    const saved = await persist([...phrases, { id: newPhraseId(), text }]);
    if (saved) setDraft("");
  };

  const startEditing = (phrase: CatchPhrase) => {
    setEditingId(phrase.id);
    setEditingText(phrase.text);
    setError(null);
  };

  const saveEdit = async () => {
    const text = editingText.trim();
    if (!editingId || saving) return;
    if (!text) {
      setError("Catch phrases cannot be empty.");
      return;
    }
    const saved = await persist(
      phrases.map((phrase) =>
        phrase.id === editingId ? { ...phrase, text } : phrase,
      ),
    );
    if (saved) setEditingId(null);
  };

  const moveBy = (index: number, offset: -1 | 1) => {
    const targetIndex = index + offset;
    if (saving || targetIndex < 0 || targetIndex >= phrases.length) return;
    const next = [...phrases];
    [next[index], next[targetIndex]] = [next[targetIndex], next[index]];
    void persist(next);
  };

  return (
    <DeckPanel
      className="col-span-1 row-auto min-h-[240px] md:col-span-6 md:col-start-7 md:row-start-6 md:min-h-0"
      role="region"
      aria-labelledby="catch-phrases-title"
      alternativeStyle
    >
      <CardHeader className="flex h-[36px] shrink-0 grid-cols-none flex-row items-center justify-between px-3">
        <div className="flex min-w-0 items-center gap-2">
          <CardTitle
            id="catch-phrases-title"
            className="text-sm text-[#f4f4f5]"
          >
            Catch phrases
          </CardTitle>
        </div>
      </CardHeader>

      <CardContent className="flex min-h-0 flex-1 flex-col p-2">
        <form
          className="mb-2 flex shrink-0 gap-1.5"
          onSubmit={(event) => void addPhrase(event)}
        >
          <label className="sr-only" htmlFor="new-catch-phrase">
            New catch phrase
          </label>
          <input
            id="new-catch-phrase"
            type="text"
            maxLength={240}
            value={draft}
            className={cn(inputClassName, "flex-1")}
            placeholder="Add a new catch phrase…"
            disabled={loading || saving}
            onChange={(event) => setDraft(event.currentTarget.value)}
          />
          <Button
            type="submit"
            size="sm"
            className="h-8 rounded-none px-2.5"
            disabled={loading || saving || !draft.trim()}
          >
            <Plus aria-hidden="true" className="size-3.5" />
            Add
          </Button>
        </form>

        {error && (
          <div
            role="alert"
            className="mb-2 shrink-0 border border-[#874b47] bg-[#261414] px-3 py-2 text-xs text-[#efa39c]"
          >
            {error}
          </div>
        )}

        {loading ? (
          <div className="flex flex-1 items-center justify-center text-muted-foreground">
            <LoaderCircle
              aria-label="Loading catch phrases"
              className="size-5 animate-spin"
            />
          </div>
        ) : phrases.length === 0 ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-2 text-center text-muted-foreground">
            <Quote aria-hidden="true" className="size-5" />
            <p className="m-0 text-xs">No catch phrases yet.</p>
          </div>
        ) : (
          <ol className="m-0 min-h-0 flex-1 list-none overflow-y-auto p-0">
            {phrases.map((phrase, index) => (
              <li
                key={phrase.id}
                className={cn(
                  "flex min-h-9 min-w-0 items-center gap-0.5 bg-[linear-gradient(145deg,#e4e4e7,#c9c9cf_72%)] px-1",
                  dragTargetId === phrase.id &&
                    "border-[#79dce1] brightness-110",
                )}
                onDragOver={(event) => {
                  if (!draggedId || draggedId === phrase.id || saving) return;
                  event.preventDefault();
                  event.dataTransfer.dropEffect = "move";
                  setDragTargetId(phrase.id);
                }}
                onDragLeave={() =>
                  setDragTargetId((current) =>
                    current === phrase.id ? null : current,
                  )
                }
                onDrop={(event) => {
                  event.preventDefault();
                  if (draggedId && !saving) {
                    void persist(moveItem(phrases, draggedId, phrase.id));
                  }
                  setDraggedId(null);
                  setDragTargetId(null);
                }}
              >
                <button
                  type="button"
                  draggable={!saving && editingId !== phrase.id}
                  className="flex h-8 w-5 shrink-0 cursor-grab items-center justify-center text-[#71717a] outline-none hover:text-[#247f86] focus-visible:ring-1 focus-visible:ring-[#247f86] active:cursor-grabbing disabled:cursor-default disabled:opacity-40"
                  aria-label={`Drag ${phrase.text} to reorder`}
                  disabled={saving || editingId === phrase.id}
                  onDragStart={(event) => {
                    event.dataTransfer.effectAllowed = "move";
                    event.dataTransfer.setData("text/plain", phrase.id);
                    setDraggedId(phrase.id);
                  }}
                  onDragEnd={() => {
                    setDraggedId(null);
                    setDragTargetId(null);
                  }}
                >
                  <GripVertical aria-hidden="true" className="size-3.5" />
                </button>

                {editingId === phrase.id ? (
                  <input
                    type="text"
                    maxLength={240}
                    autoFocus
                    aria-label={`Edit ${phrase.text}`}
                    value={editingText}
                    className={cn(inputClassName, "bg-[#09090b] h-7 flex-1")}
                    onChange={(event) =>
                      setEditingText(event.currentTarget.value)
                    }
                    onKeyDown={(event) => {
                      if (event.key === "Enter") void saveEdit();
                      if (event.key === "Escape") setEditingId(null);
                    }}
                  />
                ) : (
                  <button
                    type="button"
                    className="min-w-0 flex-1 truncate px-1.5 text-left text-xs font-medium text-[#18181b] outline-none hover:text-[#247f86] focus-visible:ring-1 focus-visible:ring-[#247f86]"
                    title={phrase.text}
                    disabled={saving}
                    onDoubleClick={() => startEditing(phrase)}
                  >
                    {phrase.text}
                  </button>
                )}

                {editingId === phrase.id ? (
                  <>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="size-7 rounded-none text-[#247f86] hover:bg-[#d4d4d8] hover:text-[#175b60]"
                      aria-label="Save catch phrase"
                      disabled={saving}
                      onClick={() => void saveEdit()}
                    >
                      <Check aria-hidden="true" className="size-3.5" />
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="size-7 rounded-none text-[#52525b] hover:bg-[#d4d4d8] hover:text-[#18181b]"
                      aria-label="Cancel editing"
                      disabled={saving}
                      onClick={() => setEditingId(null)}
                    >
                      <X aria-hidden="true" className="size-3.5" />
                    </Button>
                  </>
                ) : (
                  <>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="size-7 rounded-none text-[#52525b] hover:bg-[#d4d4d8] hover:text-[#247f86]"
                      aria-label={`Edit ${phrase.text}`}
                      disabled={saving}
                      onClick={() => startEditing(phrase)}
                    >
                      <Pencil aria-hidden="true" className="size-3" />
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="size-7 rounded-none text-[#52525b] hover:bg-[#f1c9c5] hover:text-[#8b2920]"
                      aria-label={`Remove ${phrase.text}`}
                      disabled={saving}
                      onClick={() =>
                        void persist(
                          phrases.filter((item) => item.id !== phrase.id),
                        )
                      }
                    >
                      <Trash2 aria-hidden="true" className="size-3" />
                    </Button>
                  </>
                )}
              </li>
            ))}
          </ol>
        )}
      </CardContent>
    </DeckPanel>
  );
}
