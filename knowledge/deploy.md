---
triggers: [deploy, nginx, server, 部署, 服务器]
tags: [运维, devops, 发布]
---

# 部署手册

> 内部服务器部署流程。跑通时间：2026-05-10

## 第一步：上传文件

```bash
scp -r ./dist/ user@server:/var/www/project/
```

## 第二步：重启服务

```bash
ssh user@server
sudo systemctl restart nginx
sudo systemctl restart project-api
```

## 第三步：验证

```bash
curl -I https://project.example.com/health
```

预期返回 200 OK。

## 回滚方案

如果新版本出问题，切回上一个版本：

```bash
cd /var/www/project
ln -sfn releases/v1.2.3 current
sudo systemctl restart project-api
```
