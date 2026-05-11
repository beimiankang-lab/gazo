import { createApp } from 'vue';
import ElementPlus from 'element-plus';
import 'element-plus/dist/index.css';
import 'element-plus/theme-chalk/dark/css-vars.css';
import zhCn from 'element-plus/es/locale/lang/zh-cn';
import App from './App.vue';
import { i18n } from './locales';
import './styles/global.css';

const app = createApp(App);
app.use(i18n);
app.use(ElementPlus, { locale: zhCn });
app.mount('#app');

document.documentElement.classList.add('dark');
