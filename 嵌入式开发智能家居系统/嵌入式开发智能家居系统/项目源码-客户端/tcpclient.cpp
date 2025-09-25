#include "tcpclient.h"
#include "ui_tcpclient.h"
#include <QPixmap>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonArray>
#include <QDebug>


Tcpclient::Tcpclient(QWidget *parent)
    : QWidget(parent)
    , ui(new Ui::Tcpclient)
{
    ui->setupUi(this);
    socket = new QTcpSocket;//
    socketd = new QTcpSocket;
    httphelper = new QNetworkAccessManager(this); // 添加父对象自动管理内存
    connect(httphelper, &QNetworkAccessManager::finished, this, &Tcpclient::onNetworkReplyFinished);
    T = new QTimer;
    pic_flag = 0;
}

Tcpclient::~Tcpclient()
{
    delete ui;
}


void Tcpclient::on_pushButtonconnect_clicked()
{
    if(ui->pushButtonconnect->text()=="连接")
    {
        socket->connectToHost(ui->lineEdit_ip->text(),ui->lineEdit_port->text().toInt());
        socketd->connectToHost(ui->lineEdit_ip->text(),8888);
        connect(socket,&QTcpSocket::connected,this,&Tcpclient::my_connected);
        connect(socket,&QTcpSocket::disconnected,this,&Tcpclient::my_disconnected);
        connect(socket,&QTcpSocket::readyRead,this,&Tcpclient::recv_data);
        connect(socketd,&QTcpSocket::readyRead,this,&Tcpclient::picture_data);
    }
    else
    {
        socket->disconnectFromHost();
        disconnect(socket,&QTcpSocket::connected,this,&Tcpclient::my_connected);
        disconnect(socket,&QTcpSocket::disconnected,this,&Tcpclient::my_disconnected);
    }

}

void Tcpclient::my_connected()
{
    ui->pushButtonconnect->setText("断开连接");
}
void Tcpclient::my_disconnected()
{
    ui->pushButtonconnect->setText("连接");

}
void Tcpclient::on_pushButton_get_clicked()
{
    char buf[1024]="get";
    socket->write(buf,sizeof(buf));
}
//传感器
void Tcpclient::recv_data()
{
    if(socket->bytesAvailable() < 36)
        return;
    char buf[36];
    socket->read(buf,sizeof(buf));
    //温度
    unsigned char temp = static_cast<unsigned char>(buf[5]);
    ui->label_temp->setText(QString::number(temp));
    //湿度
    unsigned char hum = static_cast<unsigned char>(buf[7]);
    ui->label_hum->setText(QString::number(hum));
    //光照
    unsigned char light = static_cast<unsigned char>(buf[20]);
    ui->label_light->setText(QString::number(light));

}


//灯
void Tcpclient::on_pushButton_ledon_clicked()
{
    char buf[1024]="led_on";
    socket->write(buf,sizeof(buf));
}
void Tcpclient::on_pushButton_led_off_clicked()
{
    char buf[1024]="led_off";
    socket->write(buf,sizeof(buf));
}

//蜂鸣器

void Tcpclient::on_pushButton_buzzer_on_clicked()
{
    char buf[1024]="buzzer_on";
    socket->write(buf,sizeof(buf));
}



void Tcpclient::on_pushButton_buzzer_off_clicked()
{
    char buf[1024]="buzzer_off";
    socket->write(buf,sizeof(buf));
}
//风扇


void Tcpclient::on_pushButton_fan_on_clicked()
{
    char buf[1024]="fan_on";
    socket->write(buf,sizeof(buf));
}

void Tcpclient::on_pushButton_fan_off_clicked()
{
    char buf[1024]="fan_off";
    socket->write(buf,sizeof(buf));
}
//
void Tcpclient::on_pushButton_fan_low_clicked()
{
    char buf[1024]="fan_low";
    socket->write(buf,sizeof(buf));
}

void Tcpclient::on_pushButton_fan_mid_clicked()
{
    char buf[1024]="fan_mid";
    socket->write(buf,sizeof(buf));
}

void Tcpclient::on_pushButton_fan_high_clicked()
{
    char buf[1024]="fan_high";
    socket->write(buf,sizeof(buf));
}
//A数码管
void Tcpclient::on_pushButton_nixie_tube_on_clicked()
{
    char buf[1024]="nixie_tube_on";
    socket->write(buf,sizeof(buf));
}

void Tcpclient::on_pushButton_nixie_tube_off_clicked()
{
    char buf[1024]="nixie_tube_off";
    socket->write(buf,sizeof(buf));
}

//接收图片
void Tcpclient::picture_data()
{
    //先接收图片大小
    if(pic_flag==0){
        if(socketd->bytesAvailable()<4)
            return;
        socketd->read((char*)&pic_len,sizeof(int));
        qDebug()<<"size="<<pic_len;
        pic_flag=1;
    }
    else
    {
        if(socketd->bytesAvailable()<pic_len)
            return;
        //接受图片内容并显示
        socketd->read((char*)buf,pic_len);
        QPixmap pix;
        pix.loadFromData(buf,pic_len,"JPEG");
        ui->label_pic->setPixmap(pix);
        pic_flag=0;

    }
}


void Tcpclient::on_pushButtonstart_clicked()
{
    if(ui->pushButtonstart->text()=="start")
    {
        T->start(25);
        connect(T,&QTimer::timeout,this,&Tcpclient::my_time);
        ui->pushButtonstart->setText("stop");
    }
    else
    {
        T->stop();
        disconnect(T,&QTimer::timeout,this,&Tcpclient::my_time);
        ui->pushButtonstart->setText("start");
    }
}
void Tcpclient::my_time()
{
    //发生图片的请求
    char buf[1024]="get_pic";
    socketd->write(buf,sizeof (buf));
}



void Tcpclient::on_pushButton_ai_clicked()
{
    QNetworkRequest request;
    request.setUrl(QUrl("http://127.0.0.1:11434/api/chat"));
    request.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");

    // 构建请求体
    QJsonObject requestBody;
    requestBody.insert("model", "deepseek-r1:7b");
    requestBody.insert("stream", true); // 启用流式传输

    QJsonObject userMessage;
    userMessage.insert("role", "user"); // 修正角色类型
    userMessage.insert("content", ui->textEdit_up->toPlainText());

    QJsonArray messages;
    messages.append(userMessage);
    requestBody.insert("messages", messages);

    QJsonDocument doc(requestBody);
    QByteArray postData = doc.toJson();

    // 发送请求并连接信号
    QNetworkReply *reply = httphelper->post(request, postData);
    connect(reply, &QNetworkReply::readyRead, this, &Tcpclient::onReadyRead); // 实时读取
}

void Tcpclient::onNetworkReplyFinished(QNetworkReply *reply)
{
    // 错误处理
    if (reply->error() != QNetworkReply::NoError) {
        qDebug() << "Network Error:" << reply->errorString();
        ui->textEdit_down->append("\n[错误] " + reply->errorString());
        reply->deleteLater(); // 必须释放资源
        return;
    }

    // 处理剩余数据
    QByteArray data = reply->readAll();
    QStringList lines = QString(data).split("\n", Qt::SkipEmptyParts);

    foreach (const QString &line, lines) {
        qDebug() << "Received Line:" << line;

        QJsonParseError parseError;
        QJsonDocument doc = QJsonDocument::fromJson(line.toUtf8(), &parseError);

        if (parseError.error != QJsonParseError::NoError) {
            qDebug() << "JSON Parse Error:" << parseError.errorString();
            continue;
        }

        QJsonObject obj = doc.object();
        if (obj.contains("message")) {
            QString answer = obj["message"].toObject()["content"].toString();
            if (!answer.startsWith('<')) {
                ui->textEdit_down->insertPlainText(answer);
                ui->textEdit_down->ensureCursorVisible(); // 滚动到底部
            }
        }
    }

    reply->deleteLater(); // 释放资源
}

void Tcpclient::onReadyRead()
{
    QNetworkReply *reply = qobject_cast<QNetworkReply*>(sender());
    if (!reply) return;

    while (reply->canReadLine()) {
        QByteArray line = reply->readLine().trimmed();
        qDebug() << "Stream Data:" << line;

        QJsonParseError parseError;
        QJsonDocument doc = QJsonDocument::fromJson(line, &parseError);

        if (parseError.error == QJsonParseError::NoError) {
            QJsonObject obj = doc.object();
            if (obj.contains("message")) {
                QString content = obj["message"].toObject()["content"].toString();
                if (!content.startsWith('<')) {
                    ui->textEdit_down->insertPlainText(content);
                    QCoreApplication::processEvents();
                }
            }
        }
    }
}
