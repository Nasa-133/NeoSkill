import { notFound } from 'next/navigation';

import { Badge, Button, Card, Input } from '@/components/ui';

export const dynamic = 'force-dynamic';

export default function DesignSystemPage() {
  if (process.env.NODE_ENV === 'production') {
    notFound();
  }

  return (
    <main className="ns-showcase">
      <div className="ns-showcase__content">
        <header>
          <h1>NeoSkill UI foundation</h1>
          <p>NS-004 development-only primitive preview.</p>
        </header>

        <Card>
          <h2>Buttons</h2>
          <div className="ns-showcase__group">
            <Button>Asosiy amal</Button>
            <Button variant="secondary">Ikkinchi amal</Button>
            <Button variant="danger">O‘chirish</Button>
            <Button disabled>O‘chirilgan</Button>
            <Button loading>Saqlash</Button>
          </div>
        </Card>

        <Card>
          <h2>Inputs</h2>
          <div className="ns-showcase__group">
            <div className="ns-showcase__field">
              <Input id="email" label="Email" placeholder="sizning@email.com" type="email" />
            </div>
            <div className="ns-showcase__field">
              <Input id="password" label="Parol" error="Parol majburiy." type="password" />
            </div>
          </div>
        </Card>

        <Card>
          <h2>Status badges</h2>
          <div className="ns-showcase__group">
            <Badge>Draft</Badge>
            <Badge tone="brand">Faol</Badge>
            <Badge tone="success">Tasdiqlangan</Badge>
            <Badge tone="warning">Kutilmoqda</Badge>
            <Badge tone="danger">Rad etilgan</Badge>
          </div>
        </Card>
      </div>
    </main>
  );
}
