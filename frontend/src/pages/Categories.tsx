import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Tag, Pencil, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { api, type Category } from "@/integrations/api/client";
import { toast } from "@/components/ui/use-toast";
import { cn } from "@/lib/utils";

const PRESET_COLORS = [
  "#ef4444", "#f59e0b", "#22c55e", "#3b82f6",
  "#8b5cf6", "#ec4899", "#06b6d4", "#14b8a6",
  "#f97316", "#6b7280",
];

export default function Categories() {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Category | null>(null);

  const { data: categories = [], isLoading } = useQuery({
    queryKey: ["categories"],
    queryFn: api.getCategories,
  });

  const defaults = categories.filter((c) => c.is_default);
  const custom = categories.filter((c) => !c.is_default);

  const handleDelete = async (id: string) => {
    try {
      await api.deleteCategory(id);
      qc.invalidateQueries({ queryKey: ["categories"] });
      toast({ title: "Categoria removida" });
    } catch (err: any) {
      toast({ variant: "destructive", title: "Erro", description: err.message });
    }
  };

  const openEdit = (cat: Category) => {
    setEditing(cat);
    setOpen(true);
  };

  const closeDialog = () => {
    setOpen(false);
    setEditing(null);
  };

  return (
    <div className="p-4 md:p-6 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-display font-bold">Categorias</h1>
        <Dialog open={open} onOpenChange={(v) => { if (!v) closeDialog(); else setOpen(true); }}>
          <DialogTrigger asChild>
            <Button size="sm"><Plus className="h-4 w-4 mr-1" /> Nova Categoria</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{editing ? "Editar Categoria" : "Nova Categoria"}</DialogTitle>
            </DialogHeader>
            <CategoryForm
              initial={editing}
              onSuccess={() => {
                closeDialog();
                qc.invalidateQueries({ queryKey: ["categories"] });
              }}
            />
          </DialogContent>
        </Dialog>
      </div>

      {isLoading ? (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-20 rounded-xl" />)}
        </div>
      ) : (
        <>
          {custom.length > 0 && (
            <div className="mb-6">
              <h2 className="text-sm font-medium text-muted-foreground mb-3">Minhas categorias</h2>
              <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {custom.map((c) => (
                  <CategoryCard key={c.id} cat={c} onEdit={openEdit} onDelete={handleDelete} />
                ))}
              </div>
            </div>
          )}

          <div>
            <h2 className="text-sm font-medium text-muted-foreground mb-3">Categorias padrão</h2>
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {defaults.map((c) => (
                <CategoryCard key={c.id} cat={c} onEdit={openEdit} onDelete={handleDelete} />
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function CategoryCard({
  cat,
  onEdit,
  onDelete,
}: {
  cat: Category;
  onEdit: (c: Category) => void;
  onDelete: (id: string) => void;
}) {
  return (
    <div className="glass rounded-xl p-4 flex items-center gap-3 group">
      <div
        className="h-10 w-10 rounded-lg flex items-center justify-center shrink-0"
        style={{ background: `${cat.color}22` }}
      >
        <Tag className="h-5 w-5" style={{ color: cat.color }} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="font-medium text-sm truncate">{cat.name}</p>
        {cat.is_default && <Badge variant="secondary" className="text-[10px] mt-0.5">Padrão</Badge>}
      </div>
      {!cat.is_default && (
        <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            onClick={() => onEdit(cat)}
            className="p-1.5 rounded-lg hover:bg-white/10 text-muted-foreground"
          >
            <Pencil className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={() => onDelete(cat.id)}
            className="p-1.5 rounded-lg hover:bg-destructive/20 hover:text-destructive text-muted-foreground"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </button>
        </div>
      )}
    </div>
  );
}

function CategoryForm({
  initial,
  onSuccess,
}: {
  initial: Category | null;
  onSuccess: () => void;
}) {
  const [name, setName] = useState(initial?.name ?? "");
  const [color, setColor] = useState(initial?.color ?? "#3b82f6");
  const [saving, setSaving] = useState(false);

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    setSaving(true);
    try {
      if (initial) {
        await api.updateCategory(initial.id, { name, color });
      } else {
        await api.createCategory({ name, color });
      }
      toast({ title: initial ? "Categoria atualizada!" : "Categoria criada!" });
      onSuccess();
    } catch (err: any) {
      toast({ variant: "destructive", title: "Erro", description: err.message });
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={save} className="space-y-4">
      <div className="space-y-1.5">
        <Label>Nome</Label>
        <Input required value={name} onChange={(e) => setName(e.target.value)} placeholder="Ex: Viagem" />
      </div>

      <div className="space-y-2">
        <Label>Cor</Label>
        <div className="flex flex-wrap gap-2">
          {PRESET_COLORS.map((c) => (
            <button
              key={c}
              type="button"
              onClick={() => setColor(c)}
              className={cn(
                "h-7 w-7 rounded-full transition-all",
                color === c && "ring-2 ring-offset-2 ring-offset-background ring-white scale-110",
              )}
              style={{ background: c }}
            />
          ))}
        </div>
      </div>

      <Button type="submit" className="w-full" disabled={saving}>
        {saving ? "Salvando..." : "Salvar"}
      </Button>
    </form>
  );
}
