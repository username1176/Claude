import { Suspense } from "react";
import LoginForm from "./LoginForm";

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="glass-card rounded-xl p-8 animate-pulse shimmer h-96" />}>
      <LoginForm />
    </Suspense>
  );
}
