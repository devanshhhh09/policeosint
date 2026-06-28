import ProtectedLayout from '@/components/layout/ProtectedLayout'
export default function Layout({ children }: { children: React.ReactNode }) {
  return <ProtectedLayout>{children}</ProtectedLayout>
}
