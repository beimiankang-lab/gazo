<script setup lang="ts">
const model = defineModel<boolean>({ required: true });
</script>

<template>
  <el-dialog
    v-model="model"
    title="Gazō 使用教程"
    width="640px"
    align-center
    :close-on-click-modal="false"
  >
    <div class="help-body">
      <section>
        <h3>快速开始</h3>
        <ol>
          <li>在左侧标签切换 <b>Danbooru</b> 或 <b>Yande.re</b> 站点</li>
          <li>填入搜索词与保存目录</li>
          <li>点击 <b>▶ 开始下载</b>,日志会实时显示在右侧</li>
          <li>两个站点可以同时运行,切换标签即可查看对方进度</li>
        </ol>
      </section>
      <section>
        <h3>搜索词</h3>
        <p>使用站点的标签语法,词语之间用空格分隔。例如:</p>
        <pre>hatsune_miku +thighhighs</pre>
        <p>具体语法请参考对应站点的 Help 页。</p>
      </section>
      <section>
        <h3>运行控制</h3>
        <ul>
          <li><b>⏸</b> 暂停,下载队列保持,可随时 <b>▶</b> 继续</li>
          <li><b>⏹</b> 中止,立即结束,已下载图片保留</li>
          <li>已下载的记录会保留在侧栏,按 <b>✕</b> 可清除后重新下载</li>
        </ul>
      </section>
      <section>
        <h3>关于已删除图片 (仅 Danbooru)</h3>
        <p>
          开启开关后会额外抓取被标记为删除的图片,结果依赖站点 API
          返回,可能需要更长时间。
        </p>
      </section>
    </div>
  </el-dialog>
</template>

<style scoped>
.help-body {
  display: flex;
  flex-direction: column;
  gap: 14px;
  max-height: 60vh;
  overflow-y: auto;
  padding-right: 8px;
}
.help-body h3 {
  font-size: 14px;
  color: var(--accent-d);
  margin-bottom: 6px;
}
.help-body p,
.help-body li {
  font-size: 13px;
  line-height: 1.7;
  color: var(--text);
}
.help-body ol,
.help-body ul {
  padding-left: 20px;
}
.help-body pre {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 8px 12px;
  font-size: 12px;
  color: var(--accent-y);
  margin: 6px 0;
  overflow-x: auto;
}
</style>