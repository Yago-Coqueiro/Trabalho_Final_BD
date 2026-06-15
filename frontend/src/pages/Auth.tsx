import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { TrendingUp, BarChart2, Brain, Shield, Eye, EyeOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/hooks/useAuth";
import { toast } from "@/components/ui/use-toast";

const BRANDING = [
  { icon: BarChart2, title: "Dashboard Completo", desc: "Visualize suas finanças em gráficos intuitivos" },
  { icon: Brain,     title: "IA que Classifica",  desc: "Categorização automática de transações" },
  { icon: Shield,    title: "Seguro & Privado",    desc: "Seus dados protegidos com criptografia" },
];

export default function Auth() {
  const { user, signIn, signUp } = useAuth();
  const navigate = useNavigate();
  const [isLogin, setIsLogin] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [showPass, setShowPass] = useState(false);

  const [form, setForm] = useState({ displayName: "", email: "", password: "" });

  useEffect(() => {
    if (user) navigate("/dashboard", { replace: true });
  }, [user, navigate]);

  const handle = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.email || !form.password) return;
    if (form.password.length < 6) {
      toast({ variant: "destructive", title: "Senha muito curta", description: "A senha deve ter ao menos 6 caracteres." });
      return;
    }
    setSubmitting(true);
    try {
      if (isLogin) {
        await signIn(form.email, form.password);
      } else {
        await signUp(form.email, form.password, form.displayName || undefined);
        toast({ title: "Conta criada!", description: "Bem-vindo ao Fluxora!" });
      }
      navigate("/dashboard", { replace: true });
    } catch (err: any) {
      toast({ variant: "destructive", title: "Erro", description: err.message ?? "Tente novamente." });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen bg-background">
      {/* Left branding — hidden on mobile */}
      <div className="hidden md:flex flex-col justify-center px-12 w-1/2 border-r border-border">
        <div className="flex items-center gap-2 mb-10">
          <TrendingUp className="h-8 w-8 text-primary" />
          <span className="text-3xl font-display font-bold gradient-text">Fluxora</span>
        </div>
        <h2 className="text-2xl font-semibold mb-2">Controle financeiro inteligente</h2>
        <p className="text-muted-foreground mb-10">Gerencie suas finanças com o poder da IA conversacional.</p>
        <div className="space-y-6">
          {BRANDING.map(({ icon: Icon, title, desc }) => (
            <div key={title} className="flex gap-4">
              <div className="h-10 w-10 rounded-lg gradient-primary flex items-center justify-center shrink-0">
                <Icon className="h-5 w-5 text-white" />
              </div>
              <div>
                <div className="font-medium">{title}</div>
                <div className="text-sm text-muted-foreground">{desc}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Right form */}
      <div className="flex flex-1 items-center justify-center px-4">
        <div className="w-full max-w-md glass rounded-xl p-8 border border-border animate-fade-in">
          <h1 className="text-2xl font-display font-bold mb-1">
            {isLogin ? "Bem-vindo de volta" : "Crie sua conta"}
          </h1>
          <p className="text-muted-foreground mb-6 text-sm">
            {isLogin ? "Entre com seu e-mail e senha" : "Preencha os dados para começar"}
          </p>

          <form onSubmit={handle} className="space-y-4">
            {!isLogin && (
              <div className="space-y-1.5">
                <Label htmlFor="name">Seu nome</Label>
                <Input
                  id="name"
                  placeholder="Nome completo"
                  value={form.displayName}
                  onChange={(e) => setForm((f) => ({ ...f, displayName: e.target.value }))}
                />
              </div>
            )}

            <div className="space-y-1.5">
              <Label htmlFor="email">E-mail</Label>
              <Input
                id="email"
                type="email"
                placeholder="seu@email.com"
                required
                value={form.email}
                onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="password">Senha</Label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPass ? "text" : "password"}
                  placeholder="••••••"
                  required
                  minLength={6}
                  value={form.password}
                  onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
                  className="pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowPass((v) => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground"
                >
                  {showPass ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            <Button type="submit" className="w-full" disabled={submitting}>
              {submitting ? (
                <span className="flex items-center gap-2">
                  <span className="h-4 w-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                  {isLogin ? "Entrando..." : "Criando conta..."}
                </span>
              ) : isLogin ? "Entrar" : "Criar conta"}
            </Button>
          </form>

          <p className="mt-6 text-center text-sm text-muted-foreground">
            {isLogin ? "Não tem conta? " : "Já tem conta? "}
            <button
              onClick={() => setIsLogin((v) => !v)}
              className="text-primary hover:underline font-medium"
            >
              {isLogin ? "Cadastre-se" : "Entre"}
            </button>
          </p>
        </div>
      </div>
    </div>
  );
}
