import type { Metadata } from 'next';
import { HomeScreen } from '@/components/screens/public/HomeScreen';
export const metadata: Metadata = { alternates: { canonical: '/' } };
export default function Page(){return <HomeScreen/>}
