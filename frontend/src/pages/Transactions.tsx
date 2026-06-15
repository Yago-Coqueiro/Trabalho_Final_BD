import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2, ArrowUpCircle, ArrowDownCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { api, type Transaction, type Category } from "@/integrations/api/client";
import { toast } from "@/components/ui/use-toast";
import { formatCurrency, formatDate } from "@/lib/utils";

export default function Transactions() {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [typeFilter, setTypeFilter] = useState<"all" | "income" | "expense">("all");
  const [catFilter, setCatFilter] = useState<string>("all");

  const { data: transactions = [], isLoading } = useQuery({
    queryKey: ["transactions"],
    queryFn: () => api.getTransactions(),
  });

  const { data: categories = [] } = useQuery({
    queryKey: ["categories"],
    queryFn: api.getCategories,
  });

  const filtered = transactions.filter((t) => {
    if (typeFilter !== "all" && t.type !== typeFilter) return false;
    if (catFilter !== "all" && t.category_id !== catFilter) return false;
    return true;
  });

  const handleDelete = async (id: string) => {
    try {
      await api.deleteTransaction(id);
      qc.invalidateQueries({ queryKey: ["transactions"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      toast({ title: "Transação removida" });
    } catch (err: any) {
      toast({ variant: "destructive", title: "Erro", description: err.message });
    }
  };

  return (
    <div className="p-4 md:p-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-display font-bold">Transações</h1>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button size="sm"><Plus className="h-4 w-4 mr-1" /> Nova Transação</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader><DialogTitle>Nova Transação</DialogTitle></DialogHeader>
            <TransactionForm
              categories={categories}
              onSuccess={() => {
                setOpen(false);
                qc.invalidateQueries({ queryKey: ["transactions"] });
                qc.invalidateQueries({ queryKey: ["dashboard"] });
              }}
            />
          </DialogContent>
        </Dialog>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-4">
        <div className="flex rounded-lg overflow-hidden border border-border">
          {(["all", "income", "expense"] as const).map((f) => (
            <button
              key={f}
              onClick={() => setTypeFilter(f)}
              className={`px-4 py-1.5 text-sm transition-colors ${typeFilter === f ? "bg-primary text-primary-foreground" : "hover:bg-white/5 text-muted-foreground"}`}
            >
              {f === "all" ? "Todas" : f === "income" ? "Receitas" : "Despesas"}
            </button>
          ))}
        </div>

        <Select value={catFilter} onValueChange={setCatFilter}>
          <SelectTrigger className="w-44">
            <SelectValue placeholder="Categoria" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todas</SelectItem>
            {categories.map((c) => (
              <SelectItem key={c.id} value={c.id}>
                <span className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full shrink-0" style={{ background: c.color }} />
                  {c.name}
                </span>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* List */}
      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-16 rounded-xl" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="glass rounded-xl p-8 text-center text-muted-foreground">
          Nenhuma transação encontrada
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map((t) => (
            <TransactionRow key={t.id} t={t} onDelete={handleDelete} />
          ))}
        </div>
      )}
    </div>
  );
}

function TransactionRow({ t, onDelete }: { t: Transaction; onDelete: (id: string) => void }) {
  const isIncome = t.type === "income";
  return (
    <div className="glass rounded-xl px-4 py-3 flex items-center gap-3 group animate-fade-in">
      <div style={{ color: t.category_color ?? "#6b7280" }}>
        {isIncome
          ? <ArrowUpCircle className="h-8 w-8" />
          : <ArrowDownCircle className="h-8 w-8" />}
      </div>
      <div className="flex-1 min-w-0">
        <p className="font-medium text-sm truncate">{t.description || t.category_name || "Transação"}</p>
        <p className="text-xs text-muted-foreground">
          {t.category_name ?? "Sem categoria"} · {formatDate(t.date)}
          {t.status === "pending" && <span className="ml-2 text-yellow-500">(pendente)</span>}
        </p>
      </div>
      <div className="text-right">
        <p className={`font-semibold text-sm ${isIncome ? "text-green-400" : "text-red-400"}`}>
          {isIncome ? "+" : "-"}{formatCurrency(t.amount)}
        </p>
      </div>
      <button
        onClick={() => onDelete(t.id)}
        className="opacity-0 group-hover:opacity-100 transition-opacity p-1.5 rounded-lg hover:bg-destructive/20 hover:text-destructive text-muted-foreground"
      >
        <Trash2 className="h-4 w-4" />
      </button>
    </div>
  );
}

function TransactionForm({
  categories,
  onSuccess,
}: {
  categories: Category[];
  onSuccess: () => void;
}) {
  const today = new Date().toISOString().slice(0, 10);
  const [form, setForm] = useState({
    type: "expense" as "income" | "expense",
    amount: "",
    description: "",
    category_id: "",
    date: today,
  });
  const [saving, setSaving] = useState(false);

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.amount) return;
    setSaving(true);
    try {
      await api.createTransaction({
        type: form.type,
        amount: parseFloat(form.amount),
        description: form.description || undefined,
        category_id: form.category_id || undefined,
        date: form.date,
      });
      toast({ title: "Transação salva!" });
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
        <Label>Tipo</Label>
        <Select value={form.type} onValueChange={(v) => setForm((f) => ({ ...f, type: v as any }))}>
          <SelectTrigger><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="expense">Despesa</SelectItem>
            <SelectItem value="income">Receita</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-1.5">
        <Label>Valor (R$)</Label>
        <Input
          type="number"
          step="0.01"
          min="0.01"
          required
          placeholder="0,00"
          value={form.amount}
          onChange={(e) => setForm((f) => ({ ...f, amount: e.target.value }))}
        />
      </div>

      <div className="space-y-1.5">
        <Label>Descrição</Label>
        <Input
          placeholder="Opcional"
          value={form.description}
          onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
        />
      </div>

      <div className="space-y-1.5">
        <Label>Categoria</Label>
        <Select value={form.category_id} onValueChange={(v) => setForm((f) => ({ ...f, category_id: v }))}>
          <SelectTrigger><SelectValue placeholder="Selecione..." /></SelectTrigger>
          <SelectContent>
            {categories.map((c) => (
              <SelectItem key={c.id} value={c.id}>
                <span className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full shrink-0" style={{ background: c.color }} />
                  {c.name}
                </span>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-1.5">
        <Label>Data</Label>
        <Input
          type="date"
          required
          value={form.date}
          onChange={(e) => setForm((f) => ({ ...f, date: e.target.value }))}
        />
      </div>

      <Button type="submit" className="w-full" disabled={saving}>
        {saving ? "Salvando..." : "Salvar"}
      </Button>
    </form>
  );
}
